import discord
from discord.ext import commands
import yt_dlp
import asyncio

# FORZAR CARGA DE OPUS AL INICIAR
if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus('libopus.so.0')
        print("✅ Opus cargado desde libopus.so.0")
    except:
        try:
            discord.opus.load_opus('opus')
            print("✅ Opus cargado desde 'opus'")
        except:
            print("❌ No se pudo cargar Opus, usando fallback")

# Configuración de yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'quiet': True,
    'no_warnings': True,
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Cog de música listo")
        # Verificar estado de Opus
        if discord.opus.is_loaded():
            print("🎵 Opus está cargado y listo")
        else:
            print("❌ Opus NO está cargado")

    @commands.hybrid_command(name='play', description='Reproducir música')
    async def play(self, ctx, *, query: str):
        """Reproducir música desde YouTube"""
        try:
            if not ctx.author.voice:
                await ctx.send("❌ Debes estar en un canal de voz")
                return

            # Verificar Opus primero
            if not discord.opus.is_loaded():
                await ctx.send("❌ Error: El sistema de audio no está listo. Reiniciando...")
                try:
                    discord.opus.load_opus('opus')
                except:
                    pass
                return

            # Conectar al canal de voz
            if ctx.guild.id not in self.voice_clients:
                voice_client = await ctx.author.voice.channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
                print(f"🔊 Conectado al canal: {ctx.author.voice.channel.name}")

            voice_client = self.voice_clients[ctx.guild.id]

            # Buscar canción
            await ctx.send("🔍 Buscando...")
            
            def get_song():
                data = ytdl.extract_info(query, download=False)
                if 'entries' in data:
                    data = data['entries'][0]
                return data

            data = await asyncio.get_event_loop().run_in_executor(None, get_song)
            
            if not data:
                await ctx.send("❌ No se pudo encontrar la canción")
                return

            # Obtener URL del audio
            audio_url = data['url']
            
            # Crear fuente de audio CON OPUS
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            
            try:
                # Intentar con Opus primero
                source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)
                print("✅ Usando FFmpegOpusAudio")
            except:
                # Fallback a PCM
                source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
                print("✅ Usando FFmpegPCMAudio (fallback)")
            
            # Reproducir
            voice_client.play(source)
            
            embed = discord.Embed(
                title="🎵 Reproduciendo",
                description=f"**{data['title']}**",
                color=0x00ff00
            )
            embed.add_field(name="🔊 Estado", value="Opus cargado" if discord.opus.is_loaded() else "PCM", inline=True)
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
            print(f"Error en play: {e}")

    @commands.hybrid_command(name='stop', description='Detener música')
    async def stop(self, ctx):
        """Detener música y desconectar"""
        try:
            if ctx.guild.id in self.voice_clients:
                voice_client = self.voice_clients[ctx.guild.id]
                voice_client.stop()
                await voice_client.disconnect()
                del self.voice_clients[ctx.guild.id]
                await ctx.send("🛑 Música detenida")
            else:
                await ctx.send("❌ No estoy conectado a ningún canal")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @commands.hybrid_command(name='disconnect', description='Desconectar bot')
    async def disconnect(self, ctx):
        """Desconectar el bot del canal de voz"""
        await self.stop(ctx)

    @commands.hybrid_command(name='audio_status', description='Ver estado del audio')
    async def audio_status(self, ctx):
        """Verificar estado del sistema de audio"""
        embed = discord.Embed(title="🔊 Estado del Audio", color=0x00ff00)
        embed.add_field(name="Opus cargado", value="✅ Sí" if discord.opus.is_loaded() else "❌ No", inline=True)
        embed.add_field(name="Voice clients", value=str(len(self.voice_clients)), inline=True)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
