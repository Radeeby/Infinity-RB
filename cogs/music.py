import discord
from discord.ext import commands
import asyncio
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

# Configuración SIMPLIFICADA de yt-dlp
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
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
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

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        
        try:
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            print(f"Error creando audio: {e}")
            return None

    def parse_duration(self, duration):
        if not duration:
            return "Desconocida"
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

class MusicQueue:
    def __init__(self):
        self._queue = []
        self.current_song = None

    def add(self, song):
        self._queue.append(song)

    def next(self):
        if self._queue:
            self.current_song = self._queue.pop(0)
            return self.current_song
        self.current_song = None
        return None

    def clear(self):
        self._queue.clear()
        self.current_song = None

    def get_queue(self):
        return self._queue.copy()

    def is_empty(self):
        return len(self._queue) == 0

    def __len__(self):
        return len(self._queue)

class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.queue = MusicQueue()
        self.voice_client = None
        self.volume = 0.5

    async def connect(self):
        if not self.ctx.author.voice:
            return False

        try:
            if self.voice_client is None:
                self.voice_client = await self.ctx.author.voice.channel.connect()
            elif self.voice_client.channel != self.ctx.author.voice.channel:
                await self.voice_client.move_to(self.ctx.author.voice.channel)
            return True
        except Exception as e:
            print(f"Error conectando: {e}")
            return False

    async def play_next(self):
        if not self.voice_client or not self.voice_client.is_connected():
            return

        next_song = self.queue.next()
        if next_song:
            self.voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.ctx.bot.loop))
            
            embed = discord.Embed(
                title="🎵 Reproduciendo",
                description=f"**{next_song.title}**",
                color=0x00ff00
            )
            embed.add_field(name="👤 Artista", value=next_song.uploader or "Desconocido", inline=True)
            embed.add_field(name="⏱️ Duración", value=next_song.duration, inline=True)
            await self.ctx.send(embed=embed)
        else:
            await asyncio.sleep(60)
            if self.voice_client and not self.voice_client.is_playing() and self.queue.is_empty():
                await self.voice_client.disconnect()

    async def add_to_queue(self, query):
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
        if self.voice_client:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            self.queue.clear()
            await self.voice_client.disconnect()
            return True
        return False

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild_id):
        return self.players.get(guild_id)

    @commands.hybrid_command(name='play', description='Reproducir música de YouTube')
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            await ctx.send("❌ Debes estar en un canal de voz")
            return

        guild_id = ctx.guild.id
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(ctx)
        
        player = self.players[guild_id]
        
        song = await player.add_to_queue(query)
        
        if song:
            if player.voice_client.is_playing():
                embed = discord.Embed(
                    title="🎵 Añadido a la cola",
                    description=f"**{song.title}**",
                    color=0x00ff00
                )
                await ctx.send(embed=embed)
            else:
                await player.play_next()
        else:
            await ctx.send("❌ No se pudo encontrar la canción")

    @commands.hybrid_command(name='stop', description='Detener música y desconectar')
    async def stop(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player and player.voice_client:
            await player.stop_and_disconnect()
            del self.players[ctx.guild.id]
            await ctx.send("🛑 Música detenida")
        else:
            await ctx.send("❌ No hay música reproduciéndose")

    @commands.hybrid_command(name='skip', description='Saltar canción actual')
    async def skip(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player and player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
            await ctx.send("⏭️ Canción saltada")
        else:
            await ctx.send("❌ No hay música reproduciéndose")

    @commands.hybrid_command(name='pause', description='Pausar música')
    async def pause(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player and player.voice_client and player.voice_client.is_playing():
            player.voice_client.pause()
            await ctx.send("⏸️ Música pausada")
        else:
            await ctx.send("❌ No hay música reproduciéndose")

    @commands.hybrid_command(name='resume', description='Reanudar música')
    async def resume(self, ctx):
        player = self.get_player(ctx.guild.id)
        if player and player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await ctx.send("▶️ Música reanudada")
        else:
            await ctx.send("❌ No hay música pausada")

async def setup(bot):
    await bot.add_cog(Music(bot))
