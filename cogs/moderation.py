import discord
from discord.ext import commands
from discord import ui
import asyncio
from datetime import datetime, timedelta, timezone
import config
from .checks import has_admin_role

class ModerationPanel(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)  # 5 minutos de timeout
        self.bot = bot
        self.target_member = None
        self.reason = "No especificada"
    
    @ui.select(
        placeholder="🎯 Selecciona un miembro...",
        options=[],  # Se llenará dinámicamente
        custom_id="member_select"
    )
    async def select_member(self, interaction: discord.Interaction, select: ui.Select):
        member_id = int(select.values[0])
        self.target_member = interaction.guild.get_member(member_id)
        
        if not self.target_member:
            await interaction.response.send_message("❌ Miembro no encontrado.", ephemeral=True)
            return
        
        # Mostrar opciones de moderación para el miembro seleccionado
        embed = discord.Embed(
            title=f"🛠️ Panel de Moderación - {self.target_member.display_name}",
            description=f"**Usuario:** {self.target_member.mention}\n**ID:** {self.target_member.id}",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.add_field(
            name="📊 Información del Usuario",
            value=f"**Cuenta creada:** {self.target_member.created_at.strftime('%d/%m/%Y')}\n"
                  f"**Se unió:** {self.target_member.joined_at.strftime('%d/%m/%Y')}\n"
                  f"**Rol más alto:** {self.target_member.top_role.mention}",
            inline=False
        )
        
        view = ActionSelectView(self.bot, self.target_member)
        await interaction.response.edit_message(embed=embed, view=view)

class ActionSelectView(ui.View):
    def __init__(self, bot, target_member):
        super().__init__(timeout=300)
        self.bot = bot
        self.target_member = target_member
    
    @ui.select(
        placeholder="⚡ Selecciona una acción...",
        options=[
            discord.SelectOption(label="🔇 Silenciar", description="Silenciar temporalmente", emoji="🔇", value="mute"),
            discord.SelectOption(label="👢 Expulsar", description="Expulsar del servidor", emoji="👢", value="kick"),
            discord.SelectOption(label="🔨 Banear", description="Banear permanentemente", emoji="🔨", value="ban"),
            discord.SelectOption(label="⚠️ Advertir", description="Enviar advertencia", emoji="⚠️", value="warn"),
            discord.SelectOption(label="🔍 Ver información", description="Información detallada", emoji="🔍", value="info"),
            discord.SelectOption(label="⏰ Quitar silencio", description="Remover timeout", emoji="⏰", value="unmute")
        ],
        custom_id="action_select"
    )
    async def select_action(self, interaction: discord.Interaction, select: ui.Select):
        action = select.values[0]
        
        if action == "mute":
            await interaction.response.send_modal(MuteModal(self.bot, self.target_member))
        elif action == "kick":
            await interaction.response.send_modal(KickModal(self.bot, self.target_member))
        elif action == "ban":
            await interaction.response.send_modal(BanModal(self.bot, self.target_member))
        elif action == "warn":
            await interaction.response.send_modal(WarnModal(self.bot, self.target_member))
        elif action == "info":
            await self.show_user_info(interaction)
        elif action == "unmute":
            await self.unmute_user(interaction)
    
    async def show_user_info(self, interaction: discord.Interaction):
        """Mostrar información detallada del usuario"""
        member = self.target_member
        
        embed = discord.Embed(
            title=f"🔍 Información de {member.display_name}",
            color=member.color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Información básica
        embed.add_field(name="🆔 ID", value=member.id, inline=True)
        embed.add_field(name="🤖 Es Bot", value="Sí" if member.bot else "No", inline=True)
        embed.add_field(name="📅 Cuenta Creada", value=member.created_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        embed.add_field(name="📥 Se Unió", value=member.joined_at.strftime("%d/%m/%Y %H:%M"), inline=True)
        
        # Estado
        status_emoji = {
            'online': '🟢',
            'idle': '🟡', 
            'dnd': '🔴',
            'offline': '⚫'
        }
        embed.add_field(name="📱 Estado", value=f"{status_emoji.get(str(member.status), '⚫')} {str(member.status).title()}", inline=True)
        
        # Actividad
        if member.activity:
            activity_type = str(member.activity.type).split('.')[-1].title()
            embed.add_field(name="🎮 Actividad", value=f"{activity_type}: {member.activity.name}", inline=True)
        
        # Roles (mostrar solo los 5 principales)
        roles = [role.mention for role in member.roles[1:6]]  # Excluir @everyone y limitar a 5
        if roles:
            embed.add_field(name="🎭 Roles", value=", ".join(roles), inline=False)
        
        # Tiempo en el servidor
        time_in_server = datetime.now(timezone.utc) - member.joined_at
        days = time_in_server.days
        embed.add_field(name="⏰ En el servidor", value=f"{days} día{'s' if days != 1 else ''}", inline=True)
        
        # ¿Está silenciado?
        is_muted = member.timed_out_until and member.timed_out_until > datetime.now(timezone.utc)
        embed.add_field(name="🔇 Silenciado", value="Sí" if is_muted else "No", inline=True)
        
        if is_muted:
            time_left = member.timed_out_until - datetime.now(timezone.utc)
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            embed.add_field(name="⏳ Tiempo restante", value=f"{hours}h {minutes}m", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def unmute_user(self, interaction: discord.Interaction):
        """Quitar silencio al usuario"""
        try:
            member = self.target_member
            
            if not member.timed_out_until or member.timed_out_until < datetime.now(timezone.utc):
                await interaction.response.send_message("❌ Este usuario no está silenciado.", ephemeral=True)
                return
            
            await member.timeout(None, reason=f"Desilenciado por {interaction.user.display_name}")
            
            embed = discord.Embed(
                title="✅ Usuario Desilenciado",
                description=f"**Usuario:** {member.mention}\n**Acción por:** {interaction.user.mention}",
                color=config.BOT_COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para desilenciar a este usuario.", ephemeral=True)

class MuteModal(ui.Modal, title='🔇 Silenciar Usuario'):
    def __init__(self, bot, target_member):
        super().__init__()
        self.bot = bot
        self.target_member = target_member
    
    duration = ui.TextInput(
        label='Duración',
        placeholder='Ej: 30m, 2h, 1d, 30 (minutos por defecto)',
        default='30m',
        required=True
    )
    
    reason = ui.TextInput(
        label='Razón',
        placeholder='Razón del silencio...',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parsear duración
        duration_text = self.duration.value.lower().strip()
        duration = self.parse_duration(duration_text)
        
        if not duration:
            await interaction.response.send_message("❌ Formato de duración inválido. Usa: 30m, 2h, 1d, etc.", ephemeral=True)
            return
        
        try:
            # Aplicar timeout
            await self.target_member.timeout(duration, reason=f"{self.reason.value} - Por: {interaction.user.display_name}")
            
            # Crear embed de confirmación
            embed = discord.Embed(
                title="🔇 Usuario Silenciado",
                description=f"**Usuario:** {self.target_member.mention}\n"
                          f"**Duración:** {self.format_duration(duration)}\n"
                          f"**Razón:** {self.reason.value}\n"
                          f"**Moderador:** {interaction.user.mention}",
                color=config.BOT_COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Enviar DM al usuario
            try:
                dm_embed = discord.Embed(
                    title="🔇 Has sido silenciado",
                    description=f"Has sido silenciado en **{interaction.guild.name}**",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Duración", value=self.format_duration(duration), inline=True)
                dm_embed.add_field(name="Razón", value=self.reason.value, inline=True)
                dm_embed.add_field(name="Moderador", value=interaction.user.display_name, inline=True)
                dm_embed.add_field(name="Hasta", value=f"<t:{int((datetime.now(timezone.utc) + duration).timestamp())}:F>", inline=False)
                
                await self.target_member.send(embed=dm_embed)
            except:
                pass  # No se pudo enviar DM
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para silenciar a este usuario.", ephemeral=True)
    
    def parse_duration(self, duration_text):
        """Parsear duración de texto a timedelta"""
        try:
            if duration_text.isdigit():
                # Solo números - asumir minutos
                minutes = int(duration_text)
                return timedelta(minutes=minutes)
            
            # Buscar patrones como 30m, 2h, 1d
            if duration_text.endswith('m'):
                minutes = int(duration_text[:-1])
                return timedelta(minutes=minutes)
            elif duration_text.endswith('h'):
                hours = int(duration_text[:-1])
                return timedelta(hours=hours)
            elif duration_text.endswith('d'):
                days = int(duration_text[:-1])
                return timedelta(days=days)
            elif duration_text.endswith('w'):
                weeks = int(duration_text[:-1])
                return timedelta(weeks=weeks)
            
            return None
        except:
            return None
    
    def format_duration(self, duration):
        """Formatear timedelta a texto legible"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds} segundos"
        
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minutos"
        
        hours = minutes // 60
        minutes %= 60
        if hours < 24:
            return f"{hours}h {minutes}m"
        
        days = hours // 24
        hours %= 24
        if days < 7:
            return f"{days}d {hours}h"
        
        weeks = days // 7
        days %= 7
        return f"{weeks} semana{'s' if weeks > 1 else ''} {days} día{'s' if days > 1 else ''}"

class KickModal(ui.Modal, title='👢 Expulsar Usuario'):
    def __init__(self, bot, target_member):
        super().__init__()
        self.bot = bot
        self.target_member = target_member
    
    reason = ui.TextInput(
        label='Razón de la expulsión',
        placeholder='Describe por qué estás expulsando a este usuario...',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Verificar que no sea el propio usuario
            if self.target_member == interaction.user:
                await interaction.response.send_message("❌ No puedes expulsarte a ti mismo.", ephemeral=True)
                return
            
            # Verificar que no sea un administrador
            if self.target_member.guild_permissions.administrator:
                await interaction.response.send_message("❌ No puedes expulsar a un administrador.", ephemeral=True)
                return
            
            # Expulsar al usuario
            await self.target_member.kick(reason=f"{self.reason.value} - Por: {interaction.user.display_name}")
            
            # Embed de confirmación
            embed = discord.Embed(
                title="👢 Usuario Expulsado",
                description=f"**Usuario:** {self.target_member.mention}\n"
                          f"**Razón:** {self.reason.value}\n"
                          f"**Moderador:** {interaction.user.mention}",
                color=config.BOT_COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Enviar DM al usuario
            try:
                dm_embed = discord.Embed(
                    title="👢 Has sido expulsado",
                    description=f"Has sido expulsado de **{interaction.guild.name}**",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Razón", value=self.reason.value, inline=False)
                dm_embed.add_field(name="Moderador", value=interaction.user.display_name, inline=True)
                
                await self.target_member.send(embed=dm_embed)
            except:
                pass  # No se pudo enviar DM
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para expulsar a este usuario.", ephemeral=True)

class BanModal(ui.Modal, title='🔨 Banear Usuario'):
    def __init__(self, bot, target_member):
        super().__init__()
        self.bot = bot
        self.target_member = target_member
    
    delete_days = ui.TextInput(
        label='Días de mensajes a eliminar (0-7)',
        placeholder='Ej: 1, 3, 7 (días)',
        default='0',
        required=True
    )
    
    reason = ui.TextInput(
        label='Razón del baneo',
        placeholder='Describe por qué estás baneando a este usuario...',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Verificar que no sea el propio usuario
            if self.target_member == interaction.user:
                await interaction.response.send_message("❌ No puedes banear a ti mismo.", ephemeral=True)
                return
            
            # Verificar que no sea un administrador
            if self.target_member.guild_permissions.administrator:
                await interaction.response.send_message("❌ No puedes banear a un administrador.", ephemeral=True)
                return
            
            # Parsear días de mensajes a eliminar
            try:
                delete_days = min(7, max(0, int(self.delete_days.value)))
            except:
                delete_days = 0
            
            # Banear al usuario
            await self.target_member.ban(
                reason=f"{self.reason.value} - Por: {interaction.user.display_name}",
                delete_message_days=delete_days
            )
            
            # Embed de confirmación
            embed = discord.Embed(
                title="🔨 Usuario Baneado",
                description=f"**Usuario:** {self.target_member.mention}\n"
                          f"**Razón:** {self.reason.value}\n"
                          f"**Mensajes eliminados:** {delete_days} días\n"
                          f"**Moderador:** {interaction.user.mention}",
                color=config.BOT_COLORS["error"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Enviar DM al usuario
            try:
                dm_embed = discord.Embed(
                    title="🔨 Has sido baneado",
                    description=f"Has sido baneado de **{interaction.guild.name}**",
                    color=discord.Color.red()
                )
                dm_embed.add_field(name="Razón", value=self.reason.value, inline=False)
                dm_embed.add_field(name="Moderador", value=interaction.user.display_name, inline=True)
                dm_embed.add_field(name="Mensajes eliminados", value=f"{delete_days} días", inline=True)
                
                await self.target_member.send(embed=dm_embed)
            except:
                pass  # No se pudo enviar DM
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para banear a este usuario.", ephemeral=True)

class WarnModal(ui.Modal, title='⚠️ Advertir Usuario'):
    def __init__(self, bot, target_member):
        super().__init__()
        self.bot = bot
        self.target_member = target_member
    
    reason = ui.TextInput(
        label='Razón de la advertencia',
        placeholder='Describe la infracción cometida...',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Enviar advertencia por DM
            dm_embed = discord.Embed(
                title="⚠️ Advertencia",
                description=f"Has recibido una advertencia en **{interaction.guild.name}**",
                color=discord.Color.yellow(),
                timestamp=datetime.now(timezone.utc)
            )
            dm_embed.add_field(name="Razón", value=self.reason.value, inline=False)
            dm_embed.add_field(name="Moderador", value=interaction.user.display_name, inline=True)
            
            await self.target_member.send(embed=dm_embed)
            
            # Embed de confirmación
            embed = discord.Embed(
                title="⚠️ Usuario Advertido",
                description=f"**Usuario:** {self.target_member.mention}\n"
                          f"**Razón:** {self.reason.value}\n"
                          f"**Moderador:** {interaction.user.mention}",
                color=config.BOT_COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No pude enviar un DM al usuario.", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name='panel', description='Abrir panel de moderación avanzado')
    @has_admin_role()
    async def moderation_panel(self, ctx):
        """Panel de moderación avanzado con interfaz visual"""
        # Obtener lista de miembros para el select
        members = [member for member in ctx.guild.members if not member.bot]
        members.sort(key=lambda m: m.joined_at or datetime.now(timezone.utc))
        
        # Crear opciones para el select (últimos 100 miembros)
        member_options = []
        for member in members[:100]:  # Limitar a 100 miembros
            member_options.append(
                discord.SelectOption(
                    label=member.display_name,
                    description=f"ID: {member.id}",
                    value=str(member.id),
                    emoji="👤"
                )
        )
        
        # Si hay más de 100 miembros, agregar opción de búsqueda
        if len(members) > 100:
            member_options.append(
                discord.SelectOption(
                    label="🔍 Buscar más miembros...",
                    description="Usa /mod para miembros específicos",
                    value="search",
                    emoji="🔍"
                )
        )
        
        embed = discord.Embed(
            title="🛠️ Panel de Moderación Avanzado",
            description="**Selecciona un miembro del menú desplegable para comenzar.**\n\n"
                      "**Funciones disponibles:**\n"
                      "• 🔇 Silenciar usuarios (con duración personalizada)\n"
                      "• 👢 Expulsar usuarios\n"
                      "• 🔨 Banear usuarios (con eliminación de mensajes)\n"
                      "• ⚠️ Enviar advertencias\n"
                      "• 🔍 Ver información detallada\n"
                      "• ⏰ Quitar silencios",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.set_footer(text="El panel se cerrará automáticamente después de 5 minutos de inactividad")
        
        view = ModerationPanel(self.bot)
        view.children[0].options = member_options  # Actualizar opciones del select
        
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @commands.hybrid_command(name='mod', description='Moderación rápida de un usuario específico')
    @has_admin_role()
    async def quick_mod(self, ctx, usuario: discord.Member):
        """Moderación rápida para un usuario específico"""
        embed = discord.Embed(
            title=f"🛠️ Moderación Rápida - {usuario.display_name}",
            description=f"**Usuario:** {usuario.mention}\n**ID:** {usuario.id}",
            color=config.BOT_COLORS["primary"]
        )
        
        embed.add_field(
            name="📊 Información Rápida",
            value=f"**Cuenta creada:** {usuario.created_at.strftime('%d/%m/%Y')}\n"
                  f"**Se unió:** {usuario.joined_at.strftime('%d/%m/%Y')}\n"
                  f"**Rol más alto:** {usuario.top_role.mention}",
            inline=False
        )
        
        view = ActionSelectView(self.bot, usuario)
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    # Comandos tradicionales (para compatibilidad)
    
    @commands.hybrid_command(name='clear', description='Eliminar mensajes')
    @has_admin_role()
    async def clear(self, ctx, amount: int):
        if amount > 100:
            await ctx.send("❌ No puedes eliminar más de 100 mensajes a la vez", ephemeral=True)
            return
        
        if amount < 1:
            await ctx.send("❌ Debes eliminar al menos 1 mensaje", ephemeral=True)
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            msg = await ctx.send(f"✅ Eliminados {len(deleted) - 1} mensajes")
            await asyncio.sleep(5)
            await msg.delete()
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar mensajes en este canal")
        except Exception as e:
            await ctx.send(f"❌ Error al eliminar mensajes: {str(e)}")
    
    @commands.hybrid_command(name='mute', description='Silenciar a un usuario')
    @has_admin_role()
    async def mute(self, ctx, member: discord.Member, duracion: str = "30m", *, razon: str = "No especificada"):
        """Comando tradicional de mute"""
        modal = MuteModal(self.bot, member)
        modal.duration.default = duracion
        modal.reason.default = razon
        await ctx.send_modal(modal)
    
    @commands.hybrid_command(name='kick', description='Expulsar a un usuario')
    @has_admin_role()
    async def kick(self, ctx, member: discord.Member, *, razon: str = "No especificada"):
        """Comando tradicional de kick"""
        modal = KickModal(self.bot, member)
        modal.reason.default = razon
        await ctx.send_modal(modal)
    
    @commands.hybrid_command(name='ban', description='Banear a un usuario')
    @has_admin_role()
    async def ban(self, ctx, member: discord.Member, eliminar_mensajes: str = "0", *, razon: str = "No especificada"):
        """Comando tradicional de ban"""
        modal = BanModal(self.bot, member)
        modal.delete_days.default = eliminar_mensajes
        modal.reason.default = razon
        await ctx.send_modal(modal)
    
    @commands.hybrid_command(name='warn', description='Advertir a un usuario')
    @has_admin_role()
    async def warn(self, ctx, member: discord.Member, *, razon: str):
        """Comando tradicional de warn"""
        modal = WarnModal(self.bot, member)
        modal.reason.default = razon
        await ctx.send_modal(modal)
    
    @commands.hybrid_command(name='unmute', description='Quitar silencio a usuario')
    @has_admin_role()
    async def unmute(self, ctx, member: discord.Member):
        try:
            await member.timeout(None)
            
            embed = discord.Embed(
                title="✅ Usuario Desilenciado",
                description=f"**Usuario:** {member.mention}\n**Acción por:** {ctx.author.mention}",
                color=config.BOT_COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para desilenciar a este usuario")

async def setup(bot):
    await bot.add_cog(Moderation(bot))