import discord
from discord.ext import commands
from discord import ui
import config
from datetime import datetime

class AdminRolePanel(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @ui.select(
        placeholder="👑 Selecciona rol ADMIN...",
        options=[],  # Se llenará dinámicamente
        custom_id="admin_role_select"
    )
    async def select_admin_role(self, interaction: discord.Interaction, select: ui.Select):
        role_id = int(select.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Rol no encontrado.", ephemeral=True)
            return
        
        # Actualizar configuración
        config.ROLES["ADMIN"] = role.id
        
        embed = discord.Embed(
            title="✅ Rol ADMIN Actualizado",
            description=f"**Nuevo rol ADMIN:** {role.mention}\n**ID:** {role.id}",
            color=config.BOT_COLORS["success"],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 Permisos que otorga:",
            value="• Acceso al panel de moderación\n• Uso de comandos de administración\n• Gestión de tickets\n• Configuración del bot",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class NormalRolePanel(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @ui.select(
        placeholder="👥 Selecciona rol NORMAL...",
        options=[],  # Se llenará dinámicamente
        custom_id="normal_role_select"
    )
    async def select_normal_role(self, interaction: discord.Interaction, select: ui.Select):
        role_id = int(select.values[0])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Rol no encontrado.", ephemeral=True)
            return
        
        # Actualizar configuración
        config.ROLES["NORMAL"] = role.id
        
        embed = discord.Embed(
            title="✅ Rol NORMAL Actualizado",
            description=f"**Nuevo rol NORMAL:** {role.mention}\n**ID:** {role.id}",
            color=config.BOT_COLORS["success"],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 Permisos que otorga:",
            value="• Comandos básicos del bot\n• Creación de tickets\n• Consultas al asistente IA",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class RoleManagementView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @ui.button(label="👑 Configurar Rol ADMIN", style=discord.ButtonStyle.primary, emoji="👑")
    async def config_admin_role(self, interaction: discord.Interaction, button: ui.Button):
        # Obtener roles del servidor (excluyendo @everyone y bots)
        roles = [role for role in interaction.guild.roles if not role.is_bot_managed() and role != interaction.guild.default_role]
        roles.sort(key=lambda r: r.position, reverse=True)
        
        # Crear opciones para el select
        role_options = []
        for role in roles[:25]:  # Discord limita a 25 opciones
            role_options.append(
                discord.SelectOption(
                    label=role.name,
                    description=f"Posición: {role.position} | ID: {role.id}",
                    value=str(role.id),
                    emoji="🔧"
                )
            )
        
        embed = discord.Embed(
            title="👑 Configurar Rol ADMIN",
            description="Selecciona el rol que tendrá permisos de **administración**:\n\n"
                      "**Este rol podrá:**\n"
                      "• Usar el panel de moderación\n• Banear/expulsar usuarios\n• Gestionar tickets\n• Configurar el bot\n• Acceder a comandos administrativos",
            color=config.BOT_COLORS["primary"]
        )
        
        if config.ROLES["ADMIN"]:
            current_role = interaction.guild.get_role(config.ROLES["ADMIN"])
            if current_role:
                embed.add_field(
                    name="🔄 Rol Actual",
                    value=f"{current_role.mention} (ID: {current_role.id})",
                    inline=False
                )
        
        view = AdminRolePanel(self.bot)
        view.children[0].options = role_options
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="👥 Configurar Rol NORMAL", style=discord.ButtonStyle.secondary, emoji="👥")
    async def config_normal_role(self, interaction: discord.Interaction, button: ui.Button):
        # Obtener roles del servidor (excluyendo @everyone y bots)
        roles = [role for role in interaction.guild.roles if not role.is_bot_managed() and role != interaction.guild.default_role]
        roles.sort(key=lambda r: r.position, reverse=True)
        
        # Crear opciones para el select
        role_options = []
        for role in roles[:25]:  # Discord limita a 25 opciones
            role_options.append(
                discord.SelectOption(
                    label=role.name,
                    description=f"Posición: {role.position} | ID: {role.id}",
                    value=str(role.id),
                    emoji="💬"
                )
            )
        
        embed = discord.Embed(
            title="👥 Configurar Rol NORMAL",
            description="Selecciona el rol que tendrá permisos **normales**:\n\n"
                      "**Este rol podrá:**\n"
                      "• Usar comandos básicos\n• Crear tickets de soporte\n• Consultar al asistente IA\n• Ver información del servidor",
            color=config.BOT_COLORS["primary"]
        )
        
        if config.ROLES["NORMAL"]:
            current_role = interaction.guild.get_role(config.ROLES["NORMAL"])
            if current_role:
                embed.add_field(
                    name="🔄 Rol Actual",
                    value=f"{current_role.mention} (ID: {current_role.id})",
                    inline=False
                )
        
        view = NormalRolePanel(self.bot)
        view.children[0].options = role_options
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="📊 Ver Configuración Actual", style=discord.ButtonStyle.success, emoji="📊")
    async def view_current_config(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="📊 Configuración Actual de Roles",
            description="Estado actual de los roles configurados en el sistema:",
            color=config.BOT_COLORS["primary"],
            timestamp=datetime.now()
        )
        
        # Rol ADMIN
        admin_role = interaction.guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            embed.add_field(
                name="👑 Rol ADMIN",
                value=f"{admin_role.mention}\n**ID:** {admin_role.id}\n**Miembros:** {len(admin_role.members)}",
                inline=True
            )
        else:
            embed.add_field(
                name="👑 Rol ADMIN",
                value=f"❌ No configurado\n**ID en config:** {config.ROLES['ADMIN']}",
                inline=True
            )
        
        # Rol NORMAL
        normal_role = interaction.guild.get_role(config.ROLES["NORMAL"])
        if normal_role:
            embed.add_field(
                name="👥 Rol NORMAL",
                value=f"{normal_role.mention}\n**ID:** {normal_role.id}\n**Miembros:** {len(normal_role.members)}",
                inline=True
            )
        else:
            embed.add_field(
                name="👥 Rol NORMAL",
                value=f"❌ No configurado\n**ID en config:** {config.ROLES['NORMAL']}",
                inline=True
            )
        
        embed.add_field(
            name="💡 Información",
            value="Los cambios se aplican inmediatamente pero requieren reinicio del bot para persistir permanentemente.",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="🔄 Resetear a Default", style=discord.ButtonStyle.danger, emoji="🔄")
    async def reset_to_default(self, interaction: discord.Interaction, button: ui.Button):
        # Restablecer a los valores por defecto del config.py
        original_admin = 1424194293408727182
        original_normal = 1424194212064268410
        
        config.ROLES["ADMIN"] = original_admin
        config.ROLES["NORMAL"] = original_normal
        
        embed = discord.Embed(
            title="🔄 Configuración Resetada",
            description="Los roles han sido restablecidos a sus valores por defecto.",
            color=config.BOT_COLORS["warning"],
            timestamp=datetime.now()
        )
        
        admin_role = interaction.guild.get_role(original_admin)
        normal_role = interaction.guild.get_role(original_normal)
        
        if admin_role:
            embed.add_field(name="👑 Rol ADMIN", value=admin_role.mention, inline=True)
        else:
            embed.add_field(name="👑 Rol ADMIN", value="❌ No encontrado", inline=True)
        
        if normal_role:
            embed.add_field(name="👥 Rol NORMAL", value=normal_role.mention, inline=True)
        else:
            embed.add_field(name="👥 Rol NORMAL", value="❌ No encontrado", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)

class Authorization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name='auth', description='Panel de autorización de roles')
    @commands.has_permissions(administrator=True)
    async def authorization_panel(self, ctx):
        """Panel de configuración de roles ADMIN y NORMAL"""
        embed = discord.Embed(
            title="🔐 Panel de Autorización de Roles",
            description="**Configura los roles ADMIN y NORMAL para el sistema:**\n\n"
                      "**👑 Rol ADMIN:**\n"
                      "• Acceso completo a moderación\n• Configuración del bot\n• Gestión de tickets\n• Comandos administrativos\n\n"
                      "**👥 Rol NORMAL:**\n"
                      "• Comandos básicos del bot\n• Creación de tickets\n• Consultas al asistente IA\n• Información del servidor",
            color=config.BOT_COLORS["primary"]
        )
        
        # Mostrar configuración actual
        admin_role = ctx.guild.get_role(config.ROLES["ADMIN"])
        normal_role = ctx.guild.get_role(config.ROLES["NORMAL"])
        
        if admin_role:
            embed.add_field(
                name="👑 Rol ADMIN Actual",
                value=f"{admin_role.mention} (ID: {admin_role.id})",
                inline=True
            )
        else:
            embed.add_field(
                name="👑 Rol ADMIN Actual",
                value="❌ No configurado o no encontrado",
                inline=True
            )
        
        if normal_role:
            embed.add_field(
                name="👥 Rol NORMAL Actual",
                value=f"{normal_role.mention} (ID: {normal_role.id})",
                inline=True
            )
        else:
            embed.add_field(
                name="👥 Rol NORMAL Actual",
                value="❌ No configurado o no encontrado",
                inline=True
            )
        
        embed.set_footer(text="Los cambios se aplican inmediatamente en esta sesión")
        
        view = RoleManagementView(self.bot)
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @commands.hybrid_command(name='check_roles', description='Verificar configuración de roles actual')
    @commands.has_permissions(administrator=True)
    async def check_roles(self, ctx):
        """Verificar la configuración actual de roles"""
        embed = discord.Embed(
            title="🔍 Verificación de Roles",
            description="Estado actual de la configuración de roles:",
            color=config.BOT_COLORS["primary"],
            timestamp=datetime.now()
        )
        
        # Verificar rol ADMIN
        admin_role = ctx.guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            embed.add_field(
                name="✅ Rol ADMIN",
                value=f"{admin_role.mention}\n**ID:** {admin_role.id}\n**Miembros:** {len(admin_role.members)}\n**Posición:** {admin_role.position}",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Rol ADMIN",
                value=f"**ID en config:** {config.ROLES['ADMIN']}\n**Estado:** No encontrado en el servidor",
                inline=False
            )
        
        # Verificar rol NORMAL
        normal_role = ctx.guild.get_role(config.ROLES["NORMAL"])
        if normal_role:
            embed.add_field(
                name="✅ Rol NORMAL",
                value=f"{normal_role.mention}\n**ID:** {normal_role.id}\n**Miembros:** {len(normal_role.members)}\n**Posición:** {normal_role.position}",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Rol NORMAL",
                value=f"**ID en config:** {config.ROLES['NORMAL']}\n**Estado:** No encontrado en el servidor",
                inline=False
            )
        
        # Verificar permisos del bot
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if admin_role and bot_member:
            can_manage = admin_role < bot_member.top_role
            embed.add_field(
                name="🔧 Permisos del Bot",
                value=f"**Puede gestionar rol ADMIN:** {'✅ Sí' if can_manage else '❌ No'}\n"
                      f"**Rol más alto del bot:** {bot_member.top_role.mention}",
                inline=False
            )
        
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Authorization(bot))