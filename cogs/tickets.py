import discord
from discord.ext import commands
from discord import ui
import asyncio
from datetime import datetime
import config
from .checks import has_admin_role
import random

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Abrir Ticket', style=discord.ButtonStyle.primary, emoji='🎫', custom_id='open_ticket')
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar si ya tiene un ticket abierto
        guild = interaction.guild
        member = interaction.user
        
        # Buscar si el miembro ya tiene un ticket abierto
        for channel in guild.channels:
            if (isinstance(channel, discord.TextChannel) and 
                channel.name.startswith(('ticket-', '🚨-emergencia-')) and 
                member in channel.members):
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return
        
        await interaction.response.send_modal(TicketModal())

class ProblemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Problemas de Cuenta', description='Recuperación, verificación, etc.', emoji='👤'),
            discord.SelectOption(label='Problemas Técnicos', description='Errores, bugs, conexión', emoji='🔧'),
            discord.SelectOption(label='Reportar Usuario', description='Reportar comportamiento inapropiado', emoji='🚨'),
            discord.SelectOption(label='Preguntas Generales', description='Otras consultas', emoji='❓'),
            discord.SelectOption(label='Llamar a Admin', description='Asistencia inmediata', emoji='📞')
        ]
        super().__init__(placeholder='Selecciona tu problema...', options=options, custom_id='problem_select')
    
    async def callback(self, interaction: discord.Interaction):
        # Verificar si ya respondió (evitar duplicados)
        if interaction.response.is_done():
            return
            
        problem_type = self.values[0]
        
        if problem_type == 'Llamar a Admin':
            await self.create_emergency_ticket(interaction)
        else:
            await self.create_normal_ticket(interaction, problem_type)
    
    async def get_or_create_category(self, guild):
        """Obtener o crear la categoría de tickets con mejor manejo de errores"""
        try:
            category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY_NAME)
            
            if not category:
                print(f"🔄 Intentando crear categoría: {config.TICKET_CATEGORY_NAME}")
                
                # Verificar permisos primero
                bot_member = guild.get_member(self.bot.user.id)
                if not bot_member.guild_permissions.manage_channels:
                    print("❌ Bot no tiene permisos para gestionar canales")
                    return None
                
                # Crear la categoría
                category = await guild.create_category(
                    config.TICKET_CATEGORY_NAME,
                    reason="Creación automática de categoría para tickets"
                )
                
                # Configurar permisos básicos para la categoría
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    bot_member: discord.PermissionOverwrite(
                        read_messages=True, 
                        send_messages=True, 
                        manage_messages=True,
                        manage_channels=True
                    )
                }
                
                # Agregar rol admin si existe
                admin_role = guild.get_role(config.ROLES["ADMIN"])
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(
                        read_messages=True, 
                        send_messages=True, 
                        manage_messages=True
                    )
                
                await category.edit(overwrites=overwrites)
                print(f"✅ Categoría de tickets creada: {category.name}")
            
            return category
            
        except discord.Forbidden as e:
            print(f"❌ Error de permisos al crear categoría: {e}")
            return None
        except Exception as e:
            print(f"❌ Error inesperado al crear categoría: {e}")
            return None
    
    async def create_emergency_ticket(self, interaction: discord.Interaction):
        # Verificar si ya tiene ticket
        guild = interaction.guild
        member = interaction.user
        
        for channel in guild.channels:
            if (isinstance(channel, discord.TextChannel) and 
                channel.name.startswith(('ticket-', '🚨-emergencia-')) and 
                member in channel.members):
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return
        
        # Obtener categoría
        category = await self.get_or_create_category(guild)
        if not category:
            await interaction.response.send_message(
                "❌ No se pudo crear el ticket. Contacta a un administrador.",
                ephemeral=True
            )
            return
        
        # Obtener número de ticket
        ticket_number = config.get_next_ticket_number()
        
        # Configurar permisos
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Agregar rol de admin
        admin_role = guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        
        # Agregar permisos para el bot
        bot_member = guild.get_member(interaction.client.user.id)
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                manage_messages=True,
                manage_channels=True
            )
        
        try:
            # Crear el canal con numeración
            ticket_channel = await category.create_text_channel(
                name=f"ticket-{ticket_number:03d}",
                topic=f"Ticket de emergencia #{ticket_number:03d} - {member.display_name}",
                overwrites=overwrites,
                reason=f"Ticket de emergencia creado por {member.display_name}"
            )
            
            # SOLO el mensaje básico del ticket
            embed = discord.Embed(
                title=f"🚨 TICKET DE EMERGENCIA #{ticket_number:03d}",
                description=f"**Usuario:** {member.mention}\n**Tipo:** Llamada a Admin\n**Prioridad:** ALTA\n**Número:** #{ticket_number:03d}",
                color=config.BOT_COLORS["primary"],
                timestamp=datetime.now()
            )
            
            view = TicketCloseView()
            mention_text = f"{member.mention}"
            if admin_role:
                mention_text += f" {admin_role.mention}"
            
            await ticket_channel.send(
                content=mention_text,
                embed=embed,
                view=view
            )
            
            await interaction.response.send_message(
                f"🎫 Ticket de emergencia creado: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Error creando ticket: {e}")
            await interaction.response.send_message(
                f"❌ Error al crear el ticket: {str(e)}",
                ephemeral=True
            )
    
    async def create_normal_ticket(self, interaction: discord.Interaction, problem_type: str):
        # Verificar si ya tiene ticket
        guild = interaction.guild
        member = interaction.user
        
        for channel in guild.channels:
            if (isinstance(channel, discord.TextChannel) and 
                channel.name.startswith(('ticket-', '🚨-emergencia-')) and 
                member in channel.members):
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return
        
        # Obtener categoría
        category = await self.get_or_create_category(guild)
        if not category:
            await interaction.response.send_message(
                "❌ No se pudo crear el ticket. Contacta a un administrador.",
                ephemeral=True
            )
            return
        
        # Obtener número de ticket
        ticket_number = config.get_next_ticket_number()
        
        # Configurar permisos
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        admin_role = guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        
        # Agregar permisos para el bot
        bot_member = guild.get_member(interaction.client.user.id)
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                manage_messages=True,
                manage_channels=True
            )
        
        try:
            # Crear el canal con numeración
            ticket_channel = await category.create_text_channel(
                name=f"ticket-{ticket_number:03d}",
                topic=f"Ticket #{ticket_number:03d} - {member.display_name} - {problem_type}",
                overwrites=overwrites,
                reason=f"Ticket creado por {member.display_name}"
            )
            
            # SOLO el mensaje básico del ticket
            embed = discord.Embed(
                title=f"🎫 NUEVO TICKET #{ticket_number:03d}",
                description=f"**Usuario:** {member.mention}\n**Problema:** {problem_type}\n**Número:** #{ticket_number:03d}",
                color=config.BOT_COLORS["primary"],
                timestamp=datetime.now()
            )
            
            view = TicketCloseView()
            await ticket_channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                f"🎫 Ticket creado: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Error creando ticket: {e}")
            await interaction.response.send_message(
                f"❌ Error al crear el ticket: {str(e)}",
                ephemeral=True
            )

class TicketCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Cerrar Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar permisos por rol
        admin_role = interaction.guild.get_role(config.ROLES["ADMIN"])
        if not (interaction.user.guild_permissions.administrator or 
                (admin_role and admin_role in interaction.user.roles)):
            await interaction.response.send_message("❌ No tienes permisos para cerrar tickets.", ephemeral=True)
            return
        
        await interaction.response.send_modal(CloseTicketModal())

class CloseTicketModal(ui.Modal, title='Cerrar Ticket'):
    reason = ui.TextInput(
        label='Razón del cierre',
        placeholder='Ej: Problema resuelto...',
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.channel
        try:
            # Obtener número de ticket del nombre del canal
            ticket_number = channel.name.replace('ticket-', '') if channel.name.startswith('ticket-') else 'N/A'
            
            embed = discord.Embed(
                title=f"🔒 Ticket #{ticket_number} Cerrado",
                description=f"**Razón:** {self.reason}\n**Cerrado por:** {interaction.user.mention}",
                color=config.BOT_COLORS["primary"]
            )
            await interaction.response.send_message(embed=embed)
            
            await asyncio.sleep(5)
            await channel.delete()
            
        except Exception as e:
            print(f"❌ Error cerrando ticket: {e}")
            await interaction.response.send_message("❌ Error al cerrar el ticket.", ephemeral=True)

class TicketModal(ui.Modal, title='Crear Ticket'):
    subject = ui.TextInput(
        label='Asunto', 
        placeholder='Breve descripción de tu problema...',
        required=True,
        max_length=100
    )
    description = ui.TextInput(
        label='Descripción detallada',
        style=discord.TextStyle.paragraph,
        placeholder='Describe tu problema en detalle...',
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Verificar si ya tiene ticket abierto ANTES de crear otro
        guild = interaction.guild
        member = interaction.user
        
        for channel in guild.channels:
            if (isinstance(channel, discord.TextChannel) and 
                channel.name.startswith(('ticket-', '🚨-emergencia-')) and 
                member in channel.members):
                await interaction.response.send_message(
                    f"❌ Ya tienes un ticket abierto: {channel.mention}",
                    ephemeral=True
                )
                return
        
        embed = discord.Embed(
            title="Nuevo Ticket - Selecciona el tipo",
            description=f"**Asunto:** {self.subject}\n**Descripción:** {self.description}",
            color=config.BOT_COLORS["primary"]
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        view = ProblemSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ProblemSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ProblemSelect())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_history = {}
        self.ia_disabled_tickets = set()  # Tickets donde la IA está desactivada
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Registrar vistas persistentes
        self.bot.add_view(TicketView())
        self.bot.add_view(TicketCloseView())
        print("✅ Vistas de tickets registradas")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Solo responder en canales de tickets
        if (isinstance(message.channel, discord.TextChannel) and 
            message.channel.name.startswith(('ticket-', '🚨-emergencia-'))):
            await self.handle_ticket_message(message)
    
    async def get_ai_assistant_response(self, message: str) -> str:
        """Obtener respuesta de la IA Gemini real"""
        try:
            # Obtener el cog de IA Assistant
            ai_cog = self.bot.get_cog('AIAssistant')
            if ai_cog and hasattr(ai_cog, 'get_ai_response'):
                # Usar la IA real de Gemini
                response = await ai_cog.get_ai_response(message, "Conversación en ticket de soporte")
                return response
            else:
                # Fallback si la IA no está disponible
                return "🤖 **Asistente IA**\n\nLamentablemente, el sistema de IA no está disponible en este momento. Por favor, describe tu problema y un administrador te ayudará pronto."
                
        except Exception as e:
            print(f"❌ Error con IA Gemini: {e}")
            return "🤖 **Asistente IA**\n\nHe tenido un problema técnico al procesar tu mensaje. Por favor, intenta reformularlo o usa `/admin` para hablar con un administrador humano."
    
    async def handle_ticket_message(self, message):
        """Manejar mensajes en canales de tickets con IA real"""
        content = message.content
        channel_id = message.channel.id
        
        # Ignorar comandos
        if content.startswith('!'):
            return
        
        # Si el mensaje es /admin, desactivar IA para este ticket y llamar admin
        if content.lower() in ['/admin', '!admin']:
            # Marcar este ticket como desactivado para IA
            self.ia_disabled_tickets.add(channel_id)
            
            admin_role = message.guild.get_role(config.ROLES["ADMIN"])
            if admin_role:
                embed = discord.Embed(
                    title="📞 SOLICITUD DE ADMINISTRADOR",
                    description=f"{message.author.mention} ha solicitado asistencia humana.\n{admin_role.mention} por favor, revisa este ticket.\n\n**La IA ha sido desactivada en este ticket.**",
                    color=config.BOT_COLORS["primary"]
                )
                await message.channel.send(embed=embed)
            return
        
        # Si la IA está desactivada para este ticket, no responder
        if channel_id in self.ia_disabled_tickets:
            return
        
        # Inicializar historial de conversación si no existe
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
        
        # Mostrar que está pensando
        thinking_msg = await message.channel.send("🤖 *Infinity RB está procesando tu mensaje...*")
        
        try:
            # Obtener respuesta de la IA REAL (Gemini)
            ai_response = await self.get_ai_assistant_response(content)
            
            # Actualizar historial de conversación
            self.conversation_history[channel_id].append({
                'user': message.author.display_name,
                'message': content,
                'bot_response': ai_response,
                'timestamp': datetime.now()
            })
            
            # Limitar el historial a los últimos 10 mensajes
            if len(self.conversation_history[channel_id]) > 10:
                self.conversation_history[channel_id] = self.conversation_history[channel_id][-10:]
            
            # Crear embed con la respuesta de la IA real
            embed = discord.Embed(
                title="🤖 Infinity RB - Asistente IA",
                description=ai_response,
                color=config.BOT_COLORS["primary"],
                timestamp=datetime.now()
            )
            
            # Verificar si estamos usando Gemini o respuestas predefinidas
            ai_cog = self.bot.get_cog('AIAssistant')
            if ai_cog and hasattr(ai_cog, 'gemini_available') and ai_cog.gemini_available:
                embed.set_footer(text="Asistente Infinity RB AI • Escribe /admin para asistencia humana")
            else:
                embed.set_footer(text="Modo respuestas predefinidas • Escribe /admin para asistencia humana")
            
            await thinking_msg.delete()
            await message.channel.send(embed=embed)
            
        except Exception as e:
            await thinking_msg.delete()
            error_embed = discord.Embed(
                title="❌ Error del Asistente IA",
                description="Lo siento, tuve un problema al procesar tu mensaje. Por favor, intenta de nuevo o escribe `/admin` para ayuda humana.",
                color=config.BOT_COLORS["error"]
            )
            await message.channel.send(embed=error_embed)
    
    @commands.hybrid_command(name='admin', description='Llamar a un administrador y desactivar IA')
    async def llamar_admin(self, ctx):
        """Llamar a un administrador y desactivar IA en este ticket"""
        if not ctx.channel.name.startswith(('ticket-', '🚨-emergencia-')):
            await ctx.send("❌ Este comando solo funciona en canales de tickets.", ephemeral=True)
            return
        
        # Desactivar IA para este ticket
        self.ia_disabled_tickets.add(ctx.channel.id)
        
        admin_role = ctx.guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            embed = discord.Embed(
                title="📞 SOLICITUD DE ADMINISTRADOR",
                description=f"{ctx.author.mention} ha solicitado asistencia de un administrador.\n{admin_role.mention} por favor, revisa este ticket.\n\n**La IA ha sido desactivada en este ticket.**",
                color=config.BOT_COLORS["primary"]
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No se pudo encontrar el rol de administrador.")
    
    @commands.hybrid_command(name='enable_ia', description='Reactivar la IA en este ticket')
    async def enable_ia(self, ctx):
        """Reactivar la IA en este ticket"""
        if not ctx.channel.name.startswith(('ticket-', '🚨-emergencia-')):
            await ctx.send("❌ Este comando solo funciona en canales de tickets.", ephemeral=True)
            return
        
        # Reactivar IA para este ticket
        self.ia_disabled_tickets.discard(ctx.channel.id)
        
        embed = discord.Embed(
            title="🤖 IA Reactivada",
            description="El asistente de IA ha sido reactivado en este ticket. Ahora puedo responder a tus mensajes nuevamente.",
            color=config.BOT_COLORS["success"]
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='setup', description='Configurar sistema completo de soporte')
    @has_admin_role()
    async def setup_soporte(self, ctx):
        """Configurar sistema completo de soporte con categorías y canal de tickets"""
        try:
            # Verificar permisos del bot
            bot_member = ctx.guild.get_member(self.bot.user.id)
            if not bot_member.guild_permissions.manage_channels:
                await ctx.send("❌ No tengo permisos para gestionar canales.")
                return
            
            # 1. Crear categoría "💼 Soporte"
            soporte_category = discord.utils.get(ctx.guild.categories, name="💼 Soporte")
            if not soporte_category:
                soporte_category = await ctx.guild.create_category("💼 Soporte")
                print(f"✅ Categoría Soporte creada: {soporte_category.name}")
            
            # 2. Crear categoría "🎫 TICKETS" (para los tickets individuales)
            tickets_category = discord.utils.get(ctx.guild.categories, name=config.TICKET_CATEGORY_NAME)
            if not tickets_category:
                # Configurar permisos para la categoría de tickets
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    bot_member: discord.PermissionOverwrite(
                        read_messages=True, 
                        send_messages=True, 
                        manage_messages=True,
                        manage_channels=True
                    )
                }
                
                # Agregar rol admin si existe
                admin_role = ctx.guild.get_role(config.ROLES["ADMIN"])
                if admin_role:
                    overwrites[admin_role] = discord.PermissionOverwrite(
                        read_messages=True, 
                        send_messages=True, 
                        manage_messages=True
                    )
                
                tickets_category = await ctx.guild.create_category(config.TICKET_CATEGORY_NAME)
                await tickets_category.edit(overwrites=overwrites)
                print(f"✅ Categoría Tickets creada: {tickets_category.name}")
            
            # 3. Crear canal "🎫-tickets" en la categoría Soporte
            tickets_channel = discord.utils.get(soporte_category.channels, name="🎫-tickets")
            if not tickets_channel:
                # Configurar permisos para el canal de tickets
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                    bot_member: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
                }
                
                tickets_channel = await soporte_category.create_text_channel(
                    "🎫-tickets",
                    topic="Sistema de tickets de soporte - Crea un ticket para recibir ayuda",
                    overwrites=overwrites
                )
                print(f"✅ Canal de tickets creado: {tickets_channel.name}")
            
            # 4. CREAR CANALES DE VOZ EN LA CATEGORÍA SOPORTE
            voice_channels = [
                "🔊 Sala de Espera",
                "🔊 Soporte 1", 
                "🔊 Soporte 2",
                "🔊 Soporte 3"
            ]
            
            created_voice_channels = []
            
            for voice_channel_name in voice_channels:
                # Verificar si el canal de voz ya existe
                existing_voice = discord.utils.get(soporte_category.voice_channels, name=voice_channel_name)
                if not existing_voice:
                    # Crear canal de voz con permisos básicos
                    voice_channel = await soporte_category.create_voice_channel(
                        voice_channel_name,
                        reason="Creación automática de canal de voz para soporte"
                    )
                    created_voice_channels.append(voice_channel)
                    print(f"✅ Canal de voz creado: {voice_channel.name}")
                else:
                    created_voice_channels.append(existing_voice)
                    print(f"ℹ️ Canal de voz ya existía: {existing_voice.name}")
            
            # 5. Enviar embed de tickets en el canal recién creado
            embed = discord.Embed(
                title="🎫 Sistema de Soporte con IA Avanzada",
                description="""**¿Necesitas ayuda? ¡Crea un ticket!** 🤖

👇 **Haz clic en el botón de abajo** para crear un ticket de soporte.

**Características del sistema:**
✨ **IA Avanzada** - Responde inteligentemente a tus preguntas
🔧 **Asistencia automática** - Ayuda inmediata con tus problemas  
📞 **Escalación humana** - Usa `/admin` para hablar con un administrador
🎯 **Respuestas contextuales** - Entiende el contexto de tu conversación
""",
                color=config.BOT_COLORS["primary"]
            )
            
            view = TicketView()
            await tickets_channel.send(embed=embed, view=view)
            
            # 6. Mensaje de confirmación
            success_embed = discord.Embed(
                title="✅ Sistema de Soporte Configurado Completamente",
                description=f"""**Se han creado los siguientes elementos:**

📁 **Categorías:**
• `💼 Soporte` - Canal público de tickets y canales de voz
• `{config.TICKET_CATEGORY_NAME}` - Tickets privados numerados

📝 **Canales de Texto:**
• {tickets_channel.mention} - Para crear tickets

🔊 **Canales de Voz:**
• {" • ".join([vc.mention for vc in created_voice_channels])}

🤖 **Sistema de IA:**
• IA Gemini avanzada integrada
• Respuestas inteligentes y contextuales
• **NUEVO: Sistema de voz con IA**
• Usa `/admin` para desactivar IA y llamar humanos
• Usa `/enable_ia` para reactivar la IA

🎤 **Comandos de Voz:**
• `/join` - Conectar bot a canal de voz
• `/speak [mensaje]` - Hablar con IA por voz
• `/leave` - Desconectar bot

**El sistema está listo para usar.** Los usuarios pueden hacer clic en el botón del canal de tickets para recibir ayuda.""",
                color=config.BOT_COLORS["success"]
            )
            
            await ctx.send(embed=success_embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Configurando Sistema de Soporte",
                description=f"Ocurrió un error: {str(e)}",
                color=config.BOT_COLORS["error"]
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(Tickets(bot))