import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import aiohttp
import time

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_data = self.load_welcome_data()
        self.processed_members = {}  # Diccionario para evitar duplicados
    
    def load_welcome_data(self):
        """Carga la configuración de bienvenidas desde un archivo JSON"""
        try:
            with open('data/welcome_config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Crear estructura por defecto si el archivo no existe
            default_data = {}
            os.makedirs('data', exist_ok=True)
            with open('data/welcome_config.json', 'w') as f:
                json.dump(default_data, f, indent=4)
            return default_data
    
    def save_welcome_data(self):
        """Guarda la configuración de bienvenidas en un archivo JSON"""
        with open('data/welcome_config.json', 'w') as f:
            json.dump(self.welcome_data, f, indent=4)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Evento que se ejecuta cuando un miembro se une al servidor"""
        # Verificar si ya procesamos a este miembro recientemente
        member_key = f"{member.guild.id}_{member.id}"
        current_time = time.time()
        
        # Si el miembro ya fue procesado en los últimos 30 segundos, ignorar
        if member_key in self.processed_members:
            if current_time - self.processed_members[member_key] < 30:
                print(f"⚠️ Miembro {member} ya fue procesado recientemente, ignorando...")
                return
        
        # Registrar el procesamiento
        self.processed_members[member_key] = current_time
        
        # Limpiar entradas antiguas (más de 5 minutos)
        self.clean_processed_members()
        
        guild_id = str(member.guild.id)
        
        # Verificar si hay configuración para este servidor
        if guild_id not in self.welcome_data:
            return
        
        config = self.welcome_data[guild_id]
        channel_id = config.get('channel_id')
        
        if not channel_id:
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        # Obtener el mensaje y tipo de bienvenida
        message = config.get('message', '¡Bienvenido {member.mention} al servidor!')
        welcome_type = config.get('type', 'embed')  # embed, gif
        
        # Reemplazar variables en el mensaje
        formatted_message = message.format(
            member=member,
            guild=member.guild,
            member_count=member.guild.member_count
        )
        
        try:
            if welcome_type == 'embed':
                await self.send_embed_welcome(channel, member, formatted_message, config)
            elif welcome_type == 'gif':
                await self.send_gif_welcome(channel, member, formatted_message, config)
            
            print(f"✅ Mensaje de bienvenida enviado para {member}")
            
        except Exception as e:
            print(f"❌ Error enviando bienvenida para {member}: {e}")
    
    def clean_processed_members(self):
        """Limpia las entradas antiguas del diccionario de miembros procesados"""
        current_time = time.time()
        # Eliminar entradas con más de 5 minutos
        self.processed_members = {
            k: v for k, v in self.processed_members.items() 
            if current_time - v < 300  # 5 minutos
        }
    
    async def send_embed_welcome(self, channel, member, message, config):
        """Envía un mensaje de bienvenida con embed"""
        embed = discord.Embed(
            title="¡Bienvenido/a! 🎉",
            description=message,
            color=discord.Color.green()
        )
        
        # Configurar thumbnail con avatar del usuario
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Agregar campos adicionales si están configurados
        if config.get('show_join_date', True):
            embed.add_field(
                name="📅 Fecha de ingreso",
                value=f"<t:{int(member.joined_at.timestamp())}:F>",
                inline=True
            )
        
        if config.get('show_account_age', True):
            embed.add_field(
                name="🕐 Cuenta creada",
                value=f"<t:{int(member.created_at.timestamp())}:R>",
                inline=True
            )
        
        # Configurar imagen de fondo si está especificada
        if config.get('background_image'):
            embed.set_image(url=config['background_image'])
        
        await channel.send(embed=embed)
    
    async def send_gif_welcome(self, channel, member, message, config):
        """Envía un GIF de bienvenida"""
        gif_url = config.get('gif_url')
        
        if gif_url:
            embed = discord.Embed(
                title="¡Bienvenido/a! 🎉",
                description=message,
                color=discord.Color.blue()
            )
            embed.set_image(url=gif_url)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            if config.get('show_join_date', True):
                embed.add_field(
                    name="📅 Fecha de ingreso",
                    value=f"<t:{int(member.joined_at.timestamp())}:F>",
                    inline=True
                )
            
            await channel.send(embed=embed)
        else:
            # Si no hay GIF configurado, usar embed normal
            await self.send_embed_welcome(channel, member, message, config)
    
    @app_commands.command(name="setwelcome", description="Configura el canal de bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, 
                         tipo: str = "embed"):
        """Comando para configurar las bienvenidas"""
        
        # Validar el tipo
        valid_types = ["embed", "gif"]
        if tipo.lower() not in valid_types:
            await interaction.response.send_message(
                f"❌ Tipo inválido. Tipos disponibles: {', '.join(valid_types)}", 
                ephemeral=True
            )
            return
        
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            self.welcome_data[guild_id] = {}
        
        self.welcome_data[guild_id].update({
            'channel_id': channel.id,
            'type': tipo.lower(),
            'message': "¡Bienvenido {member.mention} al servidor {guild.name}! 🎉",
            'show_join_date': True,
            'show_account_age': True
        })
        
        self.save_welcome_data()
        
        embed = discord.Embed(
            title="✅ Configuración de bienvenidas actualizada",
            color=discord.Color.green()
        )
        embed.add_field(name="Canal", value=channel.mention, inline=True)
        embed.add_field(name="Tipo", value=tipo, inline=True)
        embed.add_field(name="Mensaje por defecto", value=self.welcome_data[guild_id]['message'], inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @set_welcome.autocomplete('tipo')
    async def set_welcome_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete para los tipos de bienvenida"""
        tipos = ["embed", "gif"]
        choices = [
            app_commands.Choice(name=tipo, value=tipo)
            for tipo in tipos if current.lower() in tipo.lower()
        ]
        return choices
    
    @app_commands.command(name="setwelcomemessage", description="Establece un mensaje personalizado para las bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction, mensaje: str):
        """Configura un mensaje personalizado para las bienvenidas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ Primero configura el canal de bienvenidas con `/setwelcome`", ephemeral=True)
            return
        
        # Validar que el mensaje tenga las variables necesarias
        if "{member.mention}" not in mensaje:
            await interaction.response.send_message(
                "⚠️ Recomendado: Incluye `{member.mention}` en el mensaje para mencionar al usuario",
                ephemeral=True
            )
        
        self.welcome_data[guild_id]['message'] = mensaje
        self.save_welcome_data()
        
        # Mostrar cómo se vería el mensaje con variables
        preview = mensaje.format(
            member=interaction.user,
            guild=interaction.guild,
            member_count=interaction.guild.member_count
        )
        
        embed = discord.Embed(
            title="✅ Mensaje de bienvenida actualizado",
            color=discord.Color.green()
        )
        embed.add_field(name="Mensaje configurado", value=mensaje, inline=False)
        embed.add_field(name="Vista previa", value=preview, inline=False)
        embed.add_field(
            name="Variables disponibles", 
            value="`{member.mention}` - Menciona al usuario\n`{member.name}` - Nombre del usuario\n`{guild.name}` - Nombre del servidor\n`{member_count}` - Total de miembros",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="testwelcome", description="Prueba el mensaje de bienvenida")
    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Comando para probar la bienvenida"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ No hay configuración de bienvenidas para este servidor.", ephemeral=True)
            return
        
        # Simular el evento de bienvenida
        config = self.welcome_data[guild_id]
        channel_id = config.get('channel_id')
        
        if not channel_id:
            await interaction.response.send_message("❌ No hay canal configurado para bienvenidas.", ephemeral=True)
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("❌ El canal de bienvenidas no existe.", ephemeral=True)
            return
        
        # Obtener el mensaje y tipo de bienvenida
        message = config.get('message', '¡Bienvenido {member.mention} al servidor!')
        welcome_type = config.get('type', 'embed')
        
        # Reemplazar variables en el mensaje
        formatted_message = message.format(
            member=interaction.user,
            guild=interaction.guild,
            member_count=interaction.guild.member_count
        )
        
        try:
            if welcome_type == 'embed':
                await self.send_embed_welcome(channel, interaction.user, formatted_message, config)
            elif welcome_type == 'gif':
                await self.send_gif_welcome(channel, interaction.user, formatted_message, config)
            
            await interaction.response.send_message("✅ Mensaje de bienvenida probado!", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error probando bienvenida: {e}", ephemeral=True)
    
    @app_commands.command(name="welcomebackground", description="Establece una imagen de fondo para las bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_background(self, interaction: discord.Interaction, url: str = None):
        """Configura una imagen de fondo para las bienvenidas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ Primero configura el canal de bienvenidas con `/setwelcome`", ephemeral=True)
            return
        
        if url:
            # Validar que sea una URL válida
            if not url.startswith(('http://', 'https://')):
                await interaction.response.send_message("❌ Por favor proporciona una URL válida (http:// o https://)", ephemeral=True)
                return
            
            self.welcome_data[guild_id]['background_image'] = url
            self.save_welcome_data()
            await interaction.response.send_message(f"✅ Imagen de fondo establecida!", ephemeral=True)
        else:
            # Eliminar la imagen de fondo si no se proporciona URL
            self.welcome_data[guild_id].pop('background_image', None)
            self.save_welcome_data()
            await interaction.response.send_message("✅ Imagen de fondo eliminada", ephemeral=True)
    
    @app_commands.command(name="welcomegif", description="Establece un GIF para las bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_gif(self, interaction: discord.Interaction, url: str = None):
        """Configura un GIF para las bienvenidas tipo GIF"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ Primero configura el canal de bienvenidas con `/setwelcome`", ephemeral=True)
            return
        
        if url:
            # Validar que sea una URL válida
            if not url.startswith(('http://', 'https://')):
                await interaction.response.send_message("❌ Por favor proporciona una URL válida (http:// o https://)", ephemeral=True)
                return
            
            self.welcome_data[guild_id]['gif_url'] = url
            self.save_welcome_data()
            await interaction.response.send_message(f"✅ GIF de bienvenida establecido!", ephemeral=True)
        else:
            # Eliminar el GIF si no se proporciona URL
            self.welcome_data[guild_id].pop('gif_url', None)
            self.save_welcome_data()
            await interaction.response.send_message("✅ GIF de bienvenida eliminado", ephemeral=True)
    
    @app_commands.command(name="welcomesettings", description="Configura qué información mostrar en las bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def welcome_settings(self, interaction: discord.Interaction, mostrar_fecha_ingreso: bool = True, mostrar_edad_cuenta: bool = True):
        """Configura qué información mostrar en las bienvenidas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ Primero configura el canal de bienvenidas con `/setwelcome`", ephemeral=True)
            return
        
        self.welcome_data[guild_id]['show_join_date'] = mostrar_fecha_ingreso
        self.welcome_data[guild_id]['show_account_age'] = mostrar_edad_cuenta
        self.save_welcome_data()
        
        embed = discord.Embed(
            title="✅ Configuración de bienvenidas actualizada",
            color=discord.Color.green()
        )
        embed.add_field(name="Mostrar fecha de ingreso", value="✅ Sí" if mostrar_fecha_ingreso else "❌ No", inline=True)
        embed.add_field(name="Mostrar edad de cuenta", value="✅ Sí" if mostrar_edad_cuenta else "❌ No", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="welcomeconfig", description="Muestra la configuración actual de bienvenidas")
    @app_commands.default_permissions(administrator=True)
    async def show_welcome_config(self, interaction: discord.Interaction):
        """Muestra la configuración actual de bienvenidas"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.welcome_data:
            await interaction.response.send_message("❌ No hay configuración de bienvenidas para este servidor.", ephemeral=True)
            return
        
        config = self.welcome_data[guild_id]
        channel = self.bot.get_channel(config.get('channel_id'))
        
        embed = discord.Embed(
            title="⚙️ Configuración de Bienvenidas",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Canal", value=channel.mention if channel else "No configurado", inline=True)
        embed.add_field(name="Tipo", value=config.get('type', 'embed'), inline=True)
        embed.add_field(name="Mensaje", value=config.get('message', 'Por defecto')[:100] + "..." if len(config.get('message', '')) > 100 else config.get('message', 'Por defecto'), inline=False)
        embed.add_field(name="Mostrar fecha ingreso", value="✅ Sí" if config.get('show_join_date', True) else "❌ No", inline=True)
        embed.add_field(name="Mostrar edad cuenta", value="✅ Sí" if config.get('show_account_age', True) else "❌ No", inline=True)
        
        if config.get('background_image'):
            embed.add_field(name="Imagen de fondo", value="✅ Configurada", inline=True)
        
        if config.get('gif_url'):
            embed.add_field(name="GIF personalizado", value="✅ Configurado", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
