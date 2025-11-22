import discord
from discord.ext import commands
import config
import asyncio
import os

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='/',  # SOLO SLASH
            intents=intents,
            help_command=None
        )
        self.start_time = discord.utils.utcnow()
    
    async def setup_hook(self):
        valid_cogs = ['moderation', 'music', 'welcome', 'saying', 'reactionrole', 'embedcreator', 'security', 'tickets', 'utilities', 'debug', 'ai_assistant', 'authorization']
        
        for cog_name in valid_cogs:
            try:
                await self.load_extension(f'cogs.{cog_name}')
                print(f'✅ Cog cargado: {cog_name}')
            except Exception as e:
                print(f'❌ Error cargando {cog_name}: {e}')
        
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos slash sincronizados!")
        except Exception as e:
            print(f"❌ Error sincronizando comandos slash: {e}")

    async def on_ready(self):
        print(f'✅ {self.user} está conectado!')
        print(f'📊 Conectado a {len(self.guilds)} servidores')
        
        print("🔧 Cogs cargados:")
        for cog_name in self.cogs:
            print(f"   ✅ {cog_name}")
        
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="tu servidor 👀"))

bot = MyBot()

async def is_staff(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_messages

# Check global para comandos slash (excepto utilities)
@bot.before_invoke
async def global_staff_check(ctx):
    # Si el comando es de utilities, permitir a todos
    if ctx.cog and ctx.cog.qualified_name.lower() == 'utilities':
        return
    
    # Si no es staff y no es utilities, denegar
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages):
        await ctx.send("❌ Solo el staff puede usar este comando.", ephemeral=True)
        raise commands.CheckFailure()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ Solo el staff puede usar este comando.", ephemeral=True)
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para ejecutar este comando.", ephemeral=True)
    elif isinstance(error, discord.NotFound) and "Unknown interaction" in str(error):
        return
    elif isinstance(error, discord.Forbidden):
        await ctx.send("❌ No tengo permisos para ejecutar esta acción.", ephemeral=True)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argumentos inválidos. Revisa la sintaxis del comando.", ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Faltan argumentos requeridos. Revisa la sintaxis del comando.", ephemeral=True)
    else:
        print(f"Error no manejado: {type(error).__name__}: {error}")

@bot.event
async def on_interaction_error(interaction, error):
    if isinstance(error, discord.NotFound) and "Unknown interaction" in str(error):
        return
    elif isinstance(error, discord.Forbidden):
        if interaction.response.is_done():
            await interaction.followup.send("❌ No tengo permisos para ejecutar esta acción.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No tengo permisos para ejecutar esta acción.", ephemeral=True)
    else:
        print(f"Error en interacción: {type(error).__name__}: {error}")

@bot.event
async def on_guild_join(guild):
    print(f"✅ Bot añadido al servidor: {guild.name} (ID: {guild.id})")
    
    system_channel = guild.system_channel
    if system_channel and system_channel.permissions_for(guild.me).send_messages:
        embed = discord.Embed(
            title="🤖 ¡Gracias por añadirme!",
            description="Soy Infinity RB, un bot multifunción con sistema de tickets, moderación, seguridad, casino y diversión.",
            color=config.BOT_COLORS["primary"]
        )
        embed.add_field(
            name="🔧 Comandos principales",
            value="• `/help` - Ver todos los comandos\n• `/diversion` - Comandos divertidos",
            inline=False
        )
        embed.add_field(
            name="🎰 Sistema de Casino",
            value="• `/casino` - Juegos de azar\n• `/balance` - Ver tu dinero\n• `/daily` - Recompensa diaria",
            inline=False
        )
        embed.set_footer(text="¡Disfruta del bot!")
        
        try:
            await system_channel.send(embed=embed)
        except:
            pass

@bot.event
async def on_guild_remove(guild):
    print(f"❌ Bot removido del servidor: {guild.name} (ID: {guild.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Ignorar mensajes que no sean comandos slash
    if not message.content.startswith('/'):
        return
    
    # Procesar comandos slash
    await bot.process_commands(message)

# SOLO COMANDOS ESENCIALES EN MAIN.PY - EL RESTO EN UTILITIES.PY

@bot.hybrid_command(name='help', description='Mostrar ayuda de todos los comandos')
async def help_command(ctx):
    embed = discord.Embed(
        title="🆘 Centro de Ayuda - Infinity RB",
        description="Todos los comandos usan el sistema slash `/`",
        color=config.BOT_COLORS["primary"]
    )
    
    # Comandos para TODOS
    embed.add_field(
        name="ℹ️ **Comandos para Todos**",
        value="""`/help` - Este mensaje de ayuda
`/diversion` - Panel de comandos divertidos
`/casino` - Juegos de casino
`/balance` - Ver tu dinero
`/daily` - Recompensa diaria
`/work` - Trabajar por dinero
`/idioma` - Cambiar idioma""",
        inline=False
    )
    
    # Comandos solo para STAFF
    if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages:
        embed.add_field(
            name="🔐 **Comandos de Staff**",
            value="""`/setup` - Configurar sistema completo
`/auth` - Panel de configuración de roles
`/panel` - Panel de moderación avanzado
`/mod` - Moderación rápida
`/clear` - Eliminar mensajes
`/mute` - Silenciar usuario
`/kick` - Expulsar usuario
`/ban` - Banear usuario
`/embedcreator` - Crear embeds personalizados
`/reactionrole` - Sistema de roles por reacción
`/welcome` - Configurar bienvenidas
`/status` - Estado del bot""",
            inline=False
        )
    
    embed.add_field(
        name="💡 **Nota importante**",
        value="Usa `/` y escribe el nombre del comando para ver todas las opciones disponibles con sus descripciones.",
        inline=False
    )
    
    embed.set_footer(text="Los comandos marcados con 🔐 son solo para staff")
    await ctx.send(embed=embed)

# SOLO UN COMANDO DE STAFF EN MAIN.PY
@bot.hybrid_command(name='status', description='Estado completo del bot')
@commands.check(lambda ctx: ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages)
async def bot_status(ctx):
    """Comando de estado del bot - Solo Staff"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🤖 Estado de Infinity RB",
        color=config.BOT_COLORS["primary"],
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(name="📡 Latencia", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="🔧 Cogs Cargados", value=len(bot.cogs), inline=True)
    
    # Tiempo de actividad
    uptime = discord.utils.utcnow() - bot.start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    embed.add_field(name="⏰ Tiempo activo", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name='sync', description='Sincronizar comandos (Solo Owner)')
@commands.is_owner()
async def sync_commands(ctx):
    """Sincronizar comandos slash - Solo Owner"""
    try:
        synced = await bot.tree.sync()
        
        embed = discord.Embed(
            title="✅ Comandos Sincronizados",
            description=f"Se sincronizaron {len(synced)} comandos slash",
            color=config.BOT_COLORS["success"]
        )
        
        await ctx.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.send(f"❌ Error sincronizando comandos: {e}", ephemeral=True)

if __name__ == "__main__":
    if config.BOT_TOKEN:
        print("🚀 Iniciando bot Infinity RB...")
        print("=" * 50)
        print("🎯 CONFIGURACIÓN:")
        print("   📝 Prefix: / (SOLO COMANDOS SLASH)")
        print("   🔐 Staff-only: Moderación, Welcome, ReactionRole, EmbedCreator")
        print("   🔐 Staff-only: Security, Tickets, AI Assistant, Authorization, Debug")
        print("   ℹ️  Para todos: Utilities (con casino y diversión)")
        print("=" * 50)
        print("📋 COMANDOS DISPONIBLES:")
        print("   /help - Ayuda completa")
        print("   /diversion - Comandos divertidos")
        print("   /casino - Juegos de azar")
        print("   /balance - Ver dinero")
        print("   /daily - Recompensa diaria")
        print("   /work - Trabajar por dinero")
        print("=" * 50)
        bot.run(config.BOT_TOKEN)
    else:
        print("❌ ERROR: No se encontró el token del bot en config.py")
        print("💡 Asegúrate de que tu archivo config.py tenga:")

        print("   BOT_TOKEN = 'tu_token_aqui'")


