import discord
from discord.ext import commands
import config
from .checks import has_admin_role

class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name='check_perms', description='Verificar permisos del bot')
    @has_admin_role()
    async def check_perms(self, ctx):
        """Verificar los permisos del bot en este servidor"""
        bot_member = ctx.guild.get_member(self.bot.user.id)
        
        if not bot_member:
            await ctx.send("❌ No se pudo encontrar al bot en este servidor.")
            return
        
        # Permisos importantes para el bot (corregidos)
        important_perms = [
            'administrator',
            'manage_channels', 
            'manage_roles',
            'manage_messages',
            'kick_members',
            'ban_members',
            'read_messages',
            'send_messages',
            'embed_links',
            'attach_files',
            'read_message_history',
            'add_reactions'
        ]
        
        embed = discord.Embed(
            title="🔍 Permisos del Bot",
            description=f"Verificando permisos para {self.bot.user.mention}",
            color=discord.Color.blue()
        )
        
        # Verificar permisos del canal
        channel_perms = ctx.channel.permissions_for(bot_member)
        
        for perm in important_perms:
            has_perm = getattr(channel_perms, perm)
            embed.add_field(
                name=perm.replace('_', ' ').title(),
                value="✅ Sí" if has_perm else "❌ No",
                inline=True
            )
        
        # Verificar permisos a nivel de servidor
        guild_perms = bot_member.guild_permissions
        embed.add_field(
            name="Permisos de Servidor",
            value="✅ Administrator" if guild_perms.administrator else "❌ No Administrator",
            inline=False
        )
        
        # Verificar roles configurados
        normal_role = ctx.guild.get_role(config.ROLES['NORMAL'])
        admin_role = ctx.guild.get_role(config.ROLES['ADMIN'])
        
        embed.add_field(
            name="Roles Configurados",
            value=f"**Normal:** {normal_role.mention if normal_role else '❌ No encontrado'}\n**Admin:** {admin_role.mention if admin_role else '❌ No encontrado'}",
            inline=False
        )
        
        # Verificar categoría de tickets
        ticket_category = discord.utils.get(ctx.guild.categories, name=config.TICKET_CATEGORY_NAME)
        embed.add_field(
            name="Categoría de Tickets",
            value=f"{ticket_category.mention if ticket_category else '❌ No existe'}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='fix_tickets', description='Solucionar problemas del sistema de tickets')
    @has_admin_role()
    async def fix_tickets(self, ctx):
        """Comando para solucionar problemas comunes de tickets"""
        try:
            guild = ctx.guild
            
            # 1. Verificar o crear categoría
            category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY_NAME)
            if not category:
                try:
                    category = await guild.create_category(config.TICKET_CATEGORY_NAME)
                    await ctx.send(f"✅ Categoría creada: {category.mention}")
                except discord.Forbidden:
                    await ctx.send("❌ No tengo permisos para crear categorías")
                    return
            else:
                await ctx.send(f"✅ Categoría existente: {category.mention}")
            
            # 2. Verificar permisos de la categoría
            bot_member = guild.get_member(self.bot.user.id)
            category_perms = category.permissions_for(bot_member)
            
            if not category_perms.manage_channels:
                await ctx.send("❌ No tengo permisos para gestionar canales en la categoría")
            else:
                await ctx.send("✅ Tengo permisos en la categoría")
            
            # 3. Verificar roles
            admin_role = guild.get_role(config.ROLES["ADMIN"])
            if admin_role:
                await ctx.send(f"✅ Rol admin encontrado: {admin_role.mention}")
            else:
                await ctx.send("❌ Rol admin no encontrado")
            
            # 4. Verificar sistema de IA
            ai_cog = self.bot.get_cog('AIAssistant')
            if ai_cog:
                ai_status = "✅ CONECTADA" if hasattr(ai_cog, 'gemini_available') and ai_cog.gemini_available else "❌ NO CONECTADA"
                await ctx.send(f"🤖 Asistente IA: {ai_status}")
            else:
                await ctx.send("❌ Cog de IA no cargado")
            
        except Exception as e:
            await ctx.send(f"❌ Error general: {str(e)}")
    
    # CAMBIADO: Renombrado a debug_status para evitar conflicto
    @commands.hybrid_command(name='debug_status', description='Estado de debug del bot')
    @has_admin_role()
    async def debug_status(self, ctx):
        """Ver el estado de debug del bot"""
        embed = discord.Embed(
            title="🐛 Estado de Debug",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        
        # Información del bot
        embed.add_field(name="📊 Servidores", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="⚡ Latencia", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🔧 Cogs Cargados", value=len(self.bot.cogs), inline=True)
        
        # Lista de cogs cargados
        loaded_cogs = list(self.bot.cogs.keys())
        embed.add_field(
            name="✅ Cogs Activos", 
            value=", ".join(loaded_cogs) if loaded_cogs else "Ninguno",
            inline=False
        )
        
        # Información de comandos
        total_commands = len(self.bot.commands)
        hybrid_commands = len([cmd for cmd in self.bot.commands if hasattr(cmd, 'app_command')])
        
        embed.add_field(
            name="📋 Comandos", 
            value=f"**Total:** {total_commands}\n**Híbridos:** {hybrid_commands}",
            inline=True
        )
        
        # Estado de la IA
        ai_cog = self.bot.get_cog('AIAssistant')
        if ai_cog:
            ai_status = "✅ CONECTADA" if hasattr(ai_cog, 'gemini_available') and ai_cog.gemini_available else "❌ NO CONECTADA"
            embed.add_field(name="🤖 IA Gemini", value=ai_status, inline=True)
        else:
            embed.add_field(name="🤖 IA Gemini", value="❌ NO CARGADO", inline=True)
        
        # Sistema de tickets
        tickets_cog = self.bot.get_cog('Tickets')
        if tickets_cog:
            # Contar tickets activos (canales que empiezan con 🎫- o 🚨-)
            ticket_channels = [ch for ch in ctx.guild.channels 
                             if isinstance(ch, discord.TextChannel) 
                             and ch.name.startswith(('🎫-', '🚨-'))]
            embed.add_field(name="🎫 Tickets Activos", value=len(ticket_channels), inline=True)
        else:
            embed.add_field(name="🎫 Tickets", value="❌ NO CARGADO", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='reload_cog', description='Recargar un cog específico')
    @has_admin_role()
    async def reload_cog(self, ctx, cog_name: str):
        """Recargar un cog específico"""
        valid_cogs = ['moderation', 'security', 'tickets', 'utilities', 'debug', 'ai_assistant']
        
        if cog_name not in valid_cogs:
            await ctx.send(f"❌ Cog no válido. Opciones: {', '.join(valid_cogs)}")
            return
        
        try:
            await self.bot.reload_extension(f'cogs.{cog_name}')
            await ctx.send(f"✅ Cog `{cog_name}` recargado correctamente")
        except Exception as e:
            await ctx.send(f"❌ Error recargando cog `{cog_name}`: {str(e)}")
    
    def get_uptime(self):
        delta = discord.utils.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

async def setup(bot):
    await bot.add_cog(Debug(bot))