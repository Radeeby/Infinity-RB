import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
from concurrent.futures import ThreadPoolExecutor

# Configuración de yt-dlp para obtener URLs directas
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = self.parse_duration(data.get('duration'))
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        def extract_data():
            try:
                data = ytdl.extract_info(url, download=not stream)
                if 'entries' in data:
                    data = data['entries'][0]
                return data
            except Exception as e:
                print(f"Error extrayendo datos: {e}")
                return None

        data = await loop.run_in_executor(ThreadPoolExecutor(), extract_data)
        
        if not data:
            return None

        # Obtener la URL del audio directamente
        audio_url = data['url']
        
        try:
            # Usar discord.FFmpegPCMAudio sin opciones complejas
            # Esto debería funcionar si la URL es compatible
            source = discord.FFmpegPCMAudio(audio_url)
            return cls(source, data=data)
        except Exception as e:
            print(f"Error creando fuente de audio: {e}")
            return None

    def parse_duration(self, duration):
        if not duration:
            return "Desconocida"
        
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

class MusicQueue:
    def __init__(self):
        self._queue = []
        self.loop = False
        self.loop_song = False
        self.current_song = None

    def add(self, song):
        self._queue.append(song)

    def next(self):
        if self.loop_song and self.current_song:
            return self.current_song
        
        if self.loop and self.current_song:
            self._queue.append(self.current_song)
        
        if self._queue:
            self.current_song = self._queue.pop(0)
            return self.current_song
        else:
            self.current_song = None
            return None

    def clear(self):
        self._queue.clear()
        self.current_song = None

    def remove(self, index):
        if 0 <= index < len(self._queue):
            return self._queue.pop(index)
        return None

    def get_queue(self):
        return self._queue.copy()

    def is_empty(self):
        return len(self._queue) == 0 and not self.current_song

    def __len__(self):
        return len(self._queue)

class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = MusicQueue()
        self.voice_client = None
        self.now_playing = None
        self.volume = 0.5

    async def connect(self):
        """Conectar al canal de voz del usuario"""
        if not self.ctx.author.voice:
            return False

        try:
            if self.voice_client is None:
                self.voice_client = await self.ctx.author.voice.channel.connect()
                print(f"🔊 Bot conectado al canal: {self.ctx.author.voice.channel.name}")
            elif self.voice_client.channel != self.ctx.author.voice.channel:
                await self.voice_client.move_to(self.ctx.author.voice.channel)
                print(f"🔊 Bot movido al canal: {self.ctx.author.voice.channel.name}")
            
            return True
        except Exception as e:
            print(f"❌ Error conectando al canal de voz: {e}")
            return False

    async def play_next(self):
        """Reproducir la siguiente canción en la cola"""
        if self.voice_client is None or not self.voice_client.is_connected():
            return

        next_song = self.queue.next()
        if next_song:
            self.now_playing = next_song
            
            if self.voice_client.source:
                self.voice_client.source.volume = self.volume
            
            self.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.ctx.bot.loop))
            
            channel = self.voice_client.channel
            listeners = len([member for member in channel.members if not member.bot])
            
            embed = discord.Embed(
                title="🎵 Reproduciendo Ahora",
                description=f"**{next_song.title}**",
                color=discord.Color.blue()
            )
            embed.add_field(name="👤 Artista", value=next_song.uploader or "Desconocido", inline=True)
            embed.add_field(name="⏱️ Duración", value=next_song.duration, inline=True)
            embed.add_field(name="🔊 Volumen", value=f"{int(self.volume * 100)}%", inline=True)
            embed.add_field(name="📻 Canal", value=channel.name, inline=True)
            embed.add_field(name="👥 Oyentes", value=f"{listeners} personas", inline=True)
            
            if next_song.thumbnail:
                embed.set_thumbnail(url=next_song.thumbnail)
            
            await self.ctx.send(embed=embed)
        else:
            self.now_playing = None
            embed = discord.Embed(
                title="🎵 Cola Finalizada",
                description="No hay más canciones en la cola.",
                color=discord.Color.blue()
            )
            await self.ctx.send(embed=embed)
            
            await asyncio.sleep(120)
            if self.voice_client and not self.voice_client.is_playing() and self.queue.is_empty():
                await self.voice_client.disconnect()
                print("🔇 Bot desconectado por inactividad")

    async def add_to_queue(self, query):
        """Añadir canción a la cola"""
        if not await self.connect():
            return None

        if not query.startswith(('http', 'ytsearch:')):
            query = f"ytsearch:{query}"

        async with self.ctx.typing():
            player = await YTDLSource.from_url(query, loop=self.ctx.bot.loop, stream=True)
            
        if player:
            self.queue.add(player)
            return player
        return None

    async def stop_and_disconnect(self):
        """Detener música y desconectar"""
        if self.voice_client:
            if self.voice_client.is_playing() or self.voice_client.is_paused():
                self.voice_client.stop()
            
            self.queue.clear()
            self.now_playing = None
            
            await self.voice_client.disconnect()
            return True
        return False

class MusicControls(discord.ui.View):
    def __init__(self, music_cog, ctx):
        super().__init__(timeout=180)
        self.music_cog = music_cog
        self.ctx = ctx

    @discord.ui.button(label='⏸️ Pausar', style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        if player and player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            embed = discord.Embed(description="⏸️ **Música pausada**", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay música reproduciéndose.", ephemeral=True)

    @discord.ui.button(label='▶️ Reanudar', style=discord.ButtonStyle.secondary)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        if player and player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            embed = discord.Embed(description="▶️ **Música reanudada**", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay música pausada.", ephemeral=True)

    @discord.ui.button(label='⏭️ Saltar', style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        if player and player.voice_client and (player.voice_client.is_playing() or player.voice_client.is_paused()):
            player.voice_client.stop()
            embed = discord.Embed(description="⏭️ **Canción saltada**", color=discord.Color.blue())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay música reproduciéndose.", ephemeral=True)

    @discord.ui.button(label='🔀 Mezclar', style=discord.ButtonStyle.success)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        if player and len(player.queue) > 1:
            import random
            random.shuffle(player.queue._queue)
            embed = discord.Embed(description="🔀 **Cola mezclada**", color=discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay suficientes canciones para mezclar.", ephemeral=True)

    @discord.ui.button(label='🛑 Parar', style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        if player and player.voice_client:
            success = await player.stop_and_disconnect()
            if success:
                if interaction.guild.id in self.music_cog.players:
                    del self.music_cog.players[interaction.guild.id]
                
                embed = discord.Embed(description="🛑 **Música detenida y bot desconectado**", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Error al detener la música.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No hay música reproduciéndose.", ephemeral=True)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild_id):
        return self.players.get(guild_id)

    @commands.hybrid_command(name='join', description='Unirse a tu canal de voz')
    async def join(self, ctx):
        """Hacer que el bot se una a tu canal de voz"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Error",
                description="Debes estar en un canal de voz para usar este comando.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        guild_id = ctx.guild.id
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(ctx)
        
        player = self.players[guild_id]
        
        if await player.connect():
            channel = ctx.author.voice.channel
            listeners = len([member for member in channel.members if not member.bot])
            
            embed = discord.Embed(
                title="🔊 Conectado al Canal de Voz",
                description=f"**Me he unido a:** {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="👥 Oyentes", value=f"{listeners} personas", inline=True)
            embed.add_field(name="🎵 Comando", value="Usa `/play <canción>` para empezar", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No pude conectarme al canal de voz.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='play', description='Reproducir música en el canal de voz')
    async def play(self, ctx, *, query: str):
        """Reproducir música desde YouTube para todos en el canal"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Error",
                description="Debes estar en un canal de voz para reproducir música.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        guild_id = ctx.guild.id
        
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(ctx)
        
        player = self.players[guild_id]
        
        embed = discord.Embed(
            description=f"🔍 **Buscando:** `{query}`",
            color=discord.Color.blue()
        )
        search_msg = await ctx.send(embed=embed)

        song = await player.add_to_queue(query)
        
        if song:
            queue_length = len(player.queue)
            channel = ctx.author.voice.channel
            listeners = len([member for member in channel.members if not member.bot])
            
            if player.voice_client.is_playing() or player.voice_client.is_paused():
                embed = discord.Embed(
                    title="🎵 Añadido a la Cola",
                    description=f"**{song.title}**",
                    color=discord.Color.green()
                )
                embed.add_field(name="👤 Artista", value=song.uploader or "Desconocido", inline=True)
                embed.add_field(name="⏱️ Duración", value=song.duration, inline=True)
                embed.add_field(name="📋 Posición", value=f"#{queue_length}", inline=True)
                embed.add_field(name="📻 Canal", value=channel.name, inline=True)
                embed.add_field(name="👥 Oyentes", value=f"{listeners} personas", inline=True)
                
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                
                await search_msg.edit(embed=embed)
            else:
                await search_msg.delete()
                await player.play_next()
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No se pudo encontrar o procesar la canción. Intenta con otro nombre o URL.",
                color=discord.Color.red()
            )
            await search_msg.edit(embed=embed)

    @commands.hybrid_command(name='pause', description='Pausar la música')
    async def pause(self, ctx):
        """Pausar la música para todos"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Música Pausada",
                description="La música ha sido pausada para todos los oyentes.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música reproduciéndose actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='resume', description='Reanudar la música')
    async def resume(self, ctx):
        """Reanudar la música para todos"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            embed = discord.Embed(
                title="▶️ Música Reanudada",
                description="La música ha sido reanudada para todos los oyentes.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música pausada actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='skip', description='Saltar la canción actual')
    async def skip(self, ctx):
        """Saltar canción para todos"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.voice_client and (player.voice_client.is_playing() or player.voice_client.is_paused()):
            player.voice_client.stop()
            embed = discord.Embed(
                title="⏭️ Canción Saltada",
                description="La canción actual ha sido saltada.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música reproduciéndose actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='queue', description='Mostrar la cola de reproducción')
    async def queue(self, ctx):
        """Mostrar las canciones en cola"""
        player = self.get_player(ctx.guild.id)
        
        if not player or player.queue.is_empty():
            embed = discord.Embed(
                title="📋 Cola de Reproducción",
                description="No hay canciones en la cola.\nUsa `/play <canción>` para añadir música.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        queue_list = player.queue.get_queue()
        embed = discord.Embed(
            title="📋 Cola de Reproducción",
            color=discord.Color.blue()
        )

        # Canción actual
        if player.now_playing:
            embed.add_field(
                name="🎵 Reproduciendo Ahora",
                value=f"**{player.now_playing.title}**\n`{player.now_playing.duration}` • {player.now_playing.uploader}",
                inline=False
            )

        # Próximas canciones
        if queue_list:
            queue_text = ""
            for i, song in enumerate(queue_list[:10], 1):
                queue_text += f"`{i}.` **{song.title}** - `{song.duration}`\n"
            
            if len(queue_list) > 10:
                queue_text += f"\n... y {len(queue_list) - 10} más"
            
            embed.add_field(
                name=f"⏭️ Siguientes ({len(queue_list)})",
                value=queue_text,
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='nowplaying', description='Mostrar la canción actual')
    async def nowplaying(self, ctx):
        """Mostrar información de la canción actual"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.now_playing:
            song = player.now_playing
            channel = player.voice_client.channel if player.voice_client else None
            listeners = len([member for member in channel.members if not member.bot]) if channel else 0
            
            embed = discord.Embed(
                title="🎵 Reproduciendo Ahora",
                description=f"**{song.title}**",
                color=discord.Color.blue()
            )
            embed.add_field(name="👤 Artista", value=song.uploader or "Desconocido", inline=True)
            embed.add_field(name="⏱️ Duración", value=song.duration, inline=True)
            embed.add_field(name="🔊 Volumen", value=f"{int(player.volume * 100)}%", inline=True)
            
            if channel:
                embed.add_field(name="📻 Canal", value=channel.name, inline=True)
                embed.add_field(name="👥 Oyentes", value=f"{listeners} personas", inline=True)
            
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            
            view = MusicControls(self, ctx)
            await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música reproduciéndose actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='volume', description='Ajustar el volumen (0-100)')
    async def volume(self, ctx, volume: int):
        """Ajustar el volumen para todos"""
        player = self.get_player(ctx.guild.id)
        
        if not player or not player.voice_client:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música reproduciéndose actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if 0 <= volume <= 100:
            player.volume = volume / 100
            if player.voice_client.source:
                player.voice_client.source.volume = player.volume
            
            embed = discord.Embed(
                title="🔊 Volumen Ajustado",
                description=f"Volumen establecido al **{volume}%** para todos los oyentes.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="El volumen debe estar entre 0 y 100.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='stop', description='Detener la música y desconectar el bot')
    async def stop(self, ctx):
        """Detener la música y desconectar el bot del canal de voz"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.voice_client:
            channel_name = player.voice_client.channel.name
            
            success = await player.stop_and_disconnect()
            
            if success:
                if ctx.guild.id in self.players:
                    del self.players[ctx.guild.id]
                
                embed = discord.Embed(
                    title="🛑 Música Detenida",
                    description=f"La música se ha detenido y me he desconectado del canal **{channel_name}**.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudo detener la música correctamente.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay música reproduciéndose actualmente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='disconnect', description='Desconectar el bot del canal de voz')
    async def disconnect(self, ctx):
        """Desconectar el bot del canal de voz"""
        player = self.get_player(ctx.guild.id)
        
        if player and player.voice_client:
            channel_name = player.voice_client.channel.name
            player.queue.clear()
            await player.voice_client.disconnect()
            del self.players[ctx.guild.id]
            
            embed = discord.Embed(
                title="👋 Desconectado",
                description=f"Me he desconectado del canal **{channel_name}**.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No estoy conectado a ningún canal de voz.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='shuffle', description='Mezclar la cola de reproducción')
    async def shuffle(self, ctx):
        """Mezclar aleatoriamente la cola de reproducción"""
        player = self.get_player(ctx.guild.id)
        
        if player and len(player.queue) > 1:
            import random
            random.shuffle(player.queue._queue)
            
            embed = discord.Embed(
                title="🔀 Cola Mezclada",
                description="Las canciones en cola han sido mezcladas aleatoriamente.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No hay suficientes canciones en la cola para mezclar.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='remove', description='Remover una canción de la cola')
    async def remove(self, ctx, index: int):
        """Remover una canción específica de la cola"""
        player = self.get_player(ctx.guild.id)
        
        if player and 1 <= index <= len(player.queue):
            removed_song = player.queue.remove(index - 1)
            
            embed = discord.Embed(
                title="🗑️ Canción Removida",
                description=f"**{removed_song.title}** ha sido removida de la cola.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Índice inválido. Usa `/queue` para ver las posiciones.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Auto-desconectar si el bot está solo en el canal de voz"""
        if member.bot:
            return
            
        player = self.get_player(member.guild.id)
        if player and player.voice_client:
            voice_channel = player.voice_client.channel
            
            # Contar usuarios reales (no bots) en el canal
            real_users = len([m for m in voice_channel.members if not m.bot])
            
            if real_users == 0:
                # El bot está solo, desconectar después de 1 minuto
                await asyncio.sleep(60)
                
                # Verificar nuevamente si sigue solo
                if (player.voice_client and 
                    player.voice_client.channel and 
                    len([m for m in player.voice_client.channel.members if not m.bot]) == 0):
                    
                    player.queue.clear()
                    await player.voice_client.disconnect()
                    if member.guild.id in self.players:
                        del self.players[member.guild.id]
                    print(f"🔇 Bot desconectado del canal {voice_channel.name} por inactividad")

async def setup(bot):
    await bot.add_cog(Music(bot))
