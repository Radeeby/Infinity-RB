import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio

class EmbedCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_sessions = {}
    
    def get_footer(self):
        """Obtiene el footer con la hora actual"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Infinity RB        [{current_time}]"
    
    async def is_staff(self, user: discord.Member):
        """Verifica si el usuario es staff (Administrador o tiene permisos de gestión)"""
        return user.guild_permissions.administrator or user.guild_permissions.manage_messages
    
    @app_commands.command(name="embedcreator", description="Abre el panel de creación de embeds - Solo Staff")
    async def embed_creator_slash(self, interaction: discord.Interaction):
        """Comando slash para el panel de embeds - Solo Staff"""
        # Verificar si es staff
        if not await self.is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎨 **Panel de Creación de Embeds**",
            description="¡Bienvenido al creador de embeds! Usa los botones de abajo para personalizar tu embed.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 **Instrucciones:**",
            value=(
                "1. **Configurar** - Personaliza título, descripción, color, etc.\n"
                "2. **Vista Previa** - Ve cómo queda tu embed\n"
                "3. **Enviar** - Elige el canal y publica tu embed\n"
                "4. **Cancelar** - Cierra el panel"
            ),
            inline=False
        )
        
        embed.set_footer(text=self.get_footer())
        
        view = EmbedMainView(interaction.user, self)
        await interaction.response.send_message(embed=embed, view=view)
        self.embed_sessions[interaction.user.id] = {
            'embed': discord.Embed(color=discord.Color.blue()),
            'message': None
        }

class EmbedMainView(discord.ui.View):
    def __init__(self, user, cog):
        super().__init__(timeout=300)
        self.user = user
        self.cog = cog
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica que el usuario que interactúa sea el dueño del panel y sea staff"""
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Este panel no es para ti.", ephemeral=True)
            return False
        
        # Verificar si sigue siendo staff
        if not await self.cog.is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return False
        
        return True
    
    @discord.ui.button(label="⚙️ Configurar", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def config_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre el menú de configuración del embed"""
        embed = discord.Embed(
            title="⚙️ **Configuración del Embed**",
            description="Selecciona qué quieres personalizar:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 **Opciones:**",
            value=(
                "**• Título** - Establece el título principal\n"
                "**• Descripción** - El contenido del embed\n"
                "**• Color** - Color de la barra lateral\n"
                "**• Thumbnail** - Imagen pequeña en la esquina\n"
                "**• Imagen** - Imagen principal del embed\n"
                "**• Campos** - Agrega campos de texto\n"
                "**• Footer** - Texto al pie del embed"
            ),
            inline=False
        )
        
        embed.set_footer(text=self.cog.get_footer())
        
        view = ConfigView(self.user, self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="👁️ Vista Previa", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Muestra una vista previa del embed actual"""
        session = self.cog.embed_sessions.get(self.user.id)
        
        if not session or not session['embed']:
            await interaction.response.send_message("❌ No hay embed para mostrar. Configura primero.", ephemeral=True)
            return
        
        # Asegurarse de que el footer esté actualizado
        current_embed = session['embed']
        if not current_embed.footer.text or "Infinity RB Y" not in current_embed.footer.text:
            current_embed.set_footer(text=self.cog.get_footer())
        
        await interaction.response.send_message("**📊 Vista Previa:**", embed=current_embed, ephemeral=True)
    
    @discord.ui.button(label="📤 Enviar", style=discord.ButtonStyle.success, emoji="📤")
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre el menú para seleccionar canal y enviar"""
        embed = discord.Embed(
            title="📤 **Enviar Embed**",
            description="Selecciona el canal donde quieres enviar el embed:",
            color=discord.Color.green()
        )
        
        embed.set_footer(text=self.cog.get_footer())
        
        view = ChannelSelectView(self.user, self.cog)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cierra el panel"""
        if self.user.id in self.cog.embed_sessions:
            del self.cog.embed_sessions[self.user.id]
        
        embed = discord.Embed(
            title="❌ **Panel Cerrado**",
            description="La creación de embed ha sido cancelada.",
            color=discord.Color.red()
        )
        embed.set_footer(text=self.cog.get_footer())
        
        await interaction.response.edit_message(embed=embed, view=None)

class ConfigView(discord.ui.View):
    def __init__(self, user, cog):
        super().__init__(timeout=300)
        self.user = user
        self.cog = cog
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica que el usuario que interactúa sea el dueño del panel y sea staff"""
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Este panel no es para ti.", ephemeral=True)
            return False
        
        # Verificar si sigue siendo staff
        if not await self.cog.is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return False
        
        return True
    
    @discord.ui.button(label="📝 Título", style=discord.ButtonStyle.primary)
    async def title_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura el título del embed"""
        modal = TitleModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📄 Descripción", style=discord.ButtonStyle.primary)
    async def description_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura la descripción del embed"""
        modal = DescriptionModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🎨 Color", style=discord.ButtonStyle.primary)
    async def color_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura el color del embed"""
        modal = ColorModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🖼️ Thumbnail", style=discord.ButtonStyle.primary)
    async def thumbnail_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura el thumbnail del embed"""
        modal = ThumbnailModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📷 Imagen", style=discord.ButtonStyle.primary)
    async def image_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configura la imagen del embed"""
        modal = ImageModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="➕ Campo", style=discord.ButtonStyle.primary)
    async def field_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Agrega un campo al embed"""
        modal = FieldModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="↩️ Volver", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Regresa al menú principal"""
        embed = discord.Embed(
            title="🎨 **Panel de Creación de Embeds**",
            description="¡Bienvenido al creador de embeds! Usa los botones de abajo para personalizar tu embed.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 **Instrucciones:**",
            value=(
                "1. **Configurar** - Personaliza título, descripción, color, etc.\n"
                "2. **Vista Previa** - Ve cómo queda tu embed\n"
                "3. **Enviar** - Elige el canal y publica tu embed\n"
                "4. **Cancelar** - Cierra el panel"
            ),
            inline=False
        )
        
        embed.set_footer(text=self.cog.get_footer())
        
        view = EmbedMainView(self.user, self.cog)
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelSelectView(discord.ui.View):
    def __init__(self, user, cog):
        super().__init__(timeout=300)
        self.user = user
        self.cog = cog
        self.add_item(ChannelSelect(self.user, self.cog))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica que el usuario que interactúa sea el dueño del panel y sea staff"""
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Este panel no es para ti.", ephemeral=True)
            return False
        
        # Verificar si sigue siendo staff
        if not await self.cog.is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return False
        
        return True

    @discord.ui.button(label="🔢 Usar ID", style=discord.ButtonStyle.primary, emoji="🔢")
    async def id_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Permite ingresar manualmente el ID del canal"""
        modal = ChannelIDModal(self.user, self.cog)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="↩️ Volver", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Regresa al menú principal"""
        embed = discord.Embed(
            title="🎨 **Panel de Creación de Embeds**",
            description="¡Bienvenido al creador de embeds! Usa los botones de abajo para personalizar tu embed.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 **Instrucciones:**",
            value=(
                "1. **Configurar** - Personaliza título, descripción, color, etc.\n"
                "2. **Vista Previa** - Ve cómo queda tu embed\n"
                "3. **Enviar** - Elige el canal y publica tu embed\n"
                "4. **Cancelar** - Cierra el panel"
            ),
            inline=False
        )
        
        embed.set_footer(text=self.cog.get_footer())
        
        view = EmbedMainView(self.user, self.cog)
        await interaction.response.edit_message(embed=embed, view=view)

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, user, cog):
        super().__init__(
            placeholder="🌐 Selecciona un canal...",
            channel_types=[discord.ChannelType.text],
            max_values=1
        )
        self.user = user
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        """Envía el embed al canal seleccionado"""
        session = self.cog.embed_sessions.get(self.user.id)
        
        if not session or not session['embed']:
            await interaction.response.send_message("❌ No hay embed para enviar.", ephemeral=True)
            return
        
        # OBTENER EL CANAL REAL
        selected_channel = self.values[0]
        
        # Verificar que sea un canal de texto
        if not isinstance(selected_channel, discord.TextChannel):
            await interaction.response.send_message("❌ Solo puedes enviar embeds a canales de texto.", ephemeral=True)
            return
        
        embed = session['embed']
        
        # Asegurar que el footer tenga la marca y hora actual
        if not embed.footer.text or "Infinity RB Y" not in embed.footer.text:
            embed.set_footer(text=self.cog.get_footer())
        
        try:
            # ENVIAR AL CANAL SELECCIONADO - CORRECCIÓN
            await selected_channel.send(embed=embed)
            
            # Mensaje de confirmación
            success_embed = discord.Embed(
                title="✅ **Embed Enviado**",
                description=f"El embed ha sido enviado exitosamente a {selected_channel.mention}",
                color=discord.Color.green()
            )
            success_embed.set_footer(text=self.cog.get_footer())
            
            # Limpiar sesión
            if self.user.id in self.cog.embed_sessions:
                del self.cog.embed_sessions[self.user.id]
            
            await interaction.response.edit_message(embed=success_embed, view=None)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ **Error**",
                description="No tengo permisos para enviar mensajes en ese canal.",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=self.cog.get_footer())
            await interaction.response.edit_message(embed=error_embed, view=None)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ **Error**",
                description=f"Ocurrió un error: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=self.cog.get_footer())
            await interaction.response.edit_message(embed=error_embed, view=None)

class ChannelIDModal(discord.ui.Modal, title="🔢 Enviar por ID de Canal"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    channel_id = discord.ui.TextInput(
        label="ID del Canal",
        placeholder="123456789012345678",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        session = self.cog.embed_sessions.get(self.user.id)
        
        if not session or not session['embed']:
            await interaction.response.send_message("❌ No hay embed para enviar.", ephemeral=True)
            return
        
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message("❌ Canal no encontrado.", ephemeral=True)
                return
            
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("❌ Solo puedes enviar embeds a canales de texto.", ephemeral=True)
                return
            
            embed = session['embed']
            
            # Asegurar que el footer tenga la marca y hora actual
            if not embed.footer.text or "Infinity RB Y" not in embed.footer.text:
                embed.set_footer(text=self.cog.get_footer())
            
            # Enviar al canal
            await channel.send(embed=embed)
            
            # Mensaje de confirmación
            success_embed = discord.Embed(
                title="✅ **Embed Enviado**",
                description=f"El embed ha sido enviado exitosamente a {channel.mention}",
                color=discord.Color.green()
            )
            success_embed.set_footer(text=self.cog.get_footer())
            
            # Limpiar sesión
            if self.user.id in self.cog.embed_sessions:
                del self.cog.embed_sessions[self.user.id]
            
            await interaction.response.edit_message(embed=success_embed, view=None)
            
        except ValueError:
            await interaction.response.send_message("❌ ID de canal inválido.", ephemeral=True)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ **Error**",
                description="No tengo permisos para enviar mensajes en ese canal.",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=self.cog.get_footer())
            await interaction.response.edit_message(embed=error_embed, view=None)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ **Error**",
                description=f"Ocurrió un error: {str(e)}",
                color=discord.Color.red()
            )
            error_embed.set_footer(text=self.cog.get_footer())
            await interaction.response.edit_message(embed=error_embed, view=None)

# Modales para la configuración
class TitleModal(discord.ui.Modal, title="📝 Configurar Título"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    title_input = discord.ui.TextInput(
        label="Título del Embed",
        placeholder="Ingresa el título aquí...",
        max_length=256,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        embed.title = self.title_input.value
        
        await interaction.response.send_message("✅ Título actualizado correctamente.", ephemeral=True)

class DescriptionModal(discord.ui.Modal, title="📄 Configurar Descripción"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    description_input = discord.ui.TextInput(
        label="Descripción del Embed",
        placeholder="Ingresa la descripción aquí...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        embed.description = self.description_input.value
        
        await interaction.response.send_message("✅ Descripción actualizada correctamente.", ephemeral=True)

class ColorModal(discord.ui.Modal, title="🎨 Configurar Color"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    color_input = discord.ui.TextInput(
        label="Color (Hex o nombre en inglés)",
        placeholder="Ej: #FF0000 o red o blue...",
        max_length=20,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        color_str = self.color_input.value.strip()
        
        try:
            if color_str.startswith('#'):
                color = discord.Color(int(color_str[1:], 16))
            else:
                # Buscar color por nombre
                color_dict = {
                    'red': discord.Color.red(),
                    'blue': discord.Color.blue(),
                    'green': discord.Color.green(),
                    'yellow': discord.Color.yellow(),
                    'purple': discord.Color.purple(),
                    'orange': discord.Color.orange(),
                    'pink': discord.Color.pink(),
                    'gold': discord.Color.gold(),
                    'teal': discord.Color.teal(),
                    'dark_blue': discord.Color.dark_blue(),
                    'dark_green': discord.Color.dark_green(),
                    'dark_red': discord.Color.dark_red(),
                    'dark_purple': discord.Color.dark_purple(),
                    'dark_gold': discord.Color.dark_gold(),
                    'dark_teal': discord.Color.dark_teal(),
                }
                color = color_dict.get(color_str.lower(), discord.Color.blue())
            
            embed.color = color
            await interaction.response.send_message(f"✅ Color actualizado a: {color_str}", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Color inválido. Usa formato HEX (#FF0000) o nombre en inglés.", ephemeral=True)

class ThumbnailModal(discord.ui.Modal, title="🖼️ Configurar Thumbnail"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    thumbnail_input = discord.ui.TextInput(
        label="URL del Thumbnail",
        placeholder="https://ejemplo.com/imagen.jpg",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        embed.set_thumbnail(url=self.thumbnail_input.value)
        
        await interaction.response.send_message("✅ Thumbnail actualizado correctamente.", ephemeral=True)

class ImageModal(discord.ui.Modal, title="📷 Configurar Imagen"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    image_input = discord.ui.TextInput(
        label="URL de la Imagen",
        placeholder="https://ejemplo.com/imagen-grande.jpg",
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        embed.set_image(url=self.image_input.value)
        
        await interaction.response.send_message("✅ Imagen actualizada correctamente.", ephemeral=True)

class FieldModal(discord.ui.Modal, title="➕ Agregar Campo"):
    def __init__(self, user, cog):
        super().__init__()
        self.user = user
        self.cog = cog
    
    field_name = discord.ui.TextInput(
        label="Nombre del Campo",
        placeholder="Ej: Información importante...",
        max_length=256,
        required=True
    )
    
    field_value = discord.ui.TextInput(
        label="Valor del Campo",
        placeholder="Este es el contenido del campo...",
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True
    )
    
    field_inline = discord.ui.TextInput(
        label="¿En línea? (true/false)",
        placeholder="true o false",
        default="true",
        max_length=5,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.user.id not in self.cog.embed_sessions:
            self.cog.embed_sessions[self.user.id] = {
                'embed': discord.Embed(color=discord.Color.blue())
            }
        
        embed = self.cog.embed_sessions[self.user.id]['embed']
        inline = self.field_inline.value.lower() == 'true'
        
        embed.add_field(
            name=self.field_name.value,
            value=self.field_value.value,
            inline=inline
        )
        
        await interaction.response.send_message("✅ Campo agregado correctamente.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmbedCreator(bot))