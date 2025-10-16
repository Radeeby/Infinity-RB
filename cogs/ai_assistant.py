import discord
from discord.ext import commands
import google.generativeai as genai
import os
import config
from datetime import datetime
import aiohttp
import random

class AIAssistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversations = {}
        
        # Configurar Google Gemini
        self.gemini_available = False
        self.gemini_model = None
        self.selected_model = None
        
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                
                # Listar modelos disponibles
                print("🔍 Buscando modelos disponibles de Gemini...")
                try:
                    models = genai.list_models()
                    available_models = [model.name for model in models]
                    print(f"✅ Se encontraron {len(available_models)} modelos disponibles")
                    
                    # Filtrar modelos que soporten generateContent
                    supported_models = []
                    for model_name in available_models:
                        model = genai.get_model(model_name)
                        if 'generateContent' in model.supported_generation_methods:
                            supported_models.append(model_name)
                    
                    print(f"📝 Modelos que soportan generateContent: {len(supported_models)}")
                    
                except Exception as e:
                    print(f"⚠️ No se pudieron listar modelos: {e}")
                    supported_models = []
                
                # Usar modelos que sabemos que funcionan
                possible_models = [
                    'models/gemini-2.0-flash',
                    'models/gemini-2.0-flash-001',
                    'models/gemini-2.0-flash-lite',
                    'models/gemini-2.0-flash-lite-001',
                    'models/gemini-pro-latest',
                    'models/gemini-flash-latest',
                ]
                
                # Probar solo los modelos que están en supported_models
                working_models = []
                for model in possible_models:
                    if model in supported_models:
                        working_models.append(model)
                
                if not working_models:
                    # Si no encontramos coincidencias, usar los primeros 3 de supported_models
                    working_models = supported_models[:3] if supported_models else []
                
                print(f"🔄 Probando {len(working_models)} modelos...")
                
                # Probar modelos
                for model_name in working_models:
                    try:
                        print(f"🔧 Probando modelo: {model_name}")
                        self.gemini_model = genai.GenerativeModel(model_name)
                        # Probar el modelo con una consulta simple
                        test_response = self.gemini_model.generate_content(
                            "Responde 'Hola' en español de manera profesional",
                            generation_config=genai.types.GenerationConfig(
                                max_output_tokens=20,
                                temperature=0.1
                            )
                        )
                        if test_response.text and len(test_response.text.strip()) > 0:
                            self.selected_model = model_name
                            self.gemini_available = True
                            print(f"✅ Modelo {model_name} funciona correctamente")
                            break
                        else:
                            print(f"⚠️ Modelo {model_name} respondió vacío")
                    except Exception as e:
                        print(f"❌ Modelo {model_name} falló: {str(e)[:100]}...")
                        continue
                
                if self.gemini_available:
                    print(f"🎯 Google Gemini configurado correctamente")
                else:
                    print("❌ No se pudo encontrar un modelo de Gemini funcional")
                    print("💡 Usando modo de respuestas predefinidas")
                    self.gemini_model = None
                    self.gemini_available = False
                    
            except Exception as e:
                print(f"❌ Error configurando Gemini: {e}")
                self.gemini_available = False
        else:
            print("❌ GEMINI_API_KEY no encontrada. Agrégalo al archivo .env")
    
    async def get_ai_response(self, message: str, context: str = "") -> str:
        """Obtener respuesta de Google Gemini con tono profesional"""
        try:
            # Si Gemini no está disponible, usar respuestas predefinidas
            if not self.gemini_available or not self.gemini_model:
                return await self.get_fallback_response(message)
            
            # Crear prompt profesional y respetuoso
            prompt = f"""Eres "Infinity RB", el asistente oficial del servidor. Eres profesional, respetuoso y siempre mantienes un tono cordial y servicial.

**Instrucciones específicas:**
- Presentarte como Infinity RB
- Ser extremadamente respetuoso y profesional
- Ofrecer ayuda de manera amable pero formal
- Centrarte en soluciones prácticas
- Si no puedes resolver algo, sugerir contactar al equipo administrativo
- Mantener respuestas concisas pero completas (máximo 150 palabras)
- Usar un lenguaje claro y accesible

**Contexto de la conversación:** {context}

**Consulta del usuario:** {message}

**Respuesta de Infinity RB:**"""
            
            # Generar respuesta con Gemini
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=600,
                    temperature=0.7,
                    top_p=0.8,
                )
            )
            
            # Verificar si la respuesta fue bloqueada o está vacía
            if not response.parts or not response.text:
                return await self.get_fallback_response(message)
            
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Error con Google Gemini: {e}")
            return await self.get_fallback_response(message)
    
    async def get_fallback_response(self, message: str) -> str:
        """Respuestas profesionales predefinidas cuando Gemini no funciona"""
        message_lower = message.lower()
        
        # Respuestas profesionales para saludos
        if any(word in message_lower for word in ['hola', 'hi', 'hello', 'buenas', 'saludos']):
            greetings = [
                "¡Hola! Soy Infinity RB, su asistente virtual. Es un placer atenderle. ¿En qué puedo ayudarle hoy?",
                "¡Buenas! Me presento, soy Infinity RB. Estoy aquí para brindarle asistencia. ¿Qué problema tiene?",
                "¡Hola! Un gusto saludarle. Soy Infinity RB, su asistente. ¿En qué puedo ser de ayuda?"
            ]
            return random.choice(greetings)
        
        # Respuestas para agradecimientos
        elif any(word in message_lower for word in ['gracias', 'thanks', 'ty', 'agradecido', 'thx']):
            thanks = [
                "De nada, es un placer poder ayudarle. ¿Hay algo más en lo que pueda asistirle?",
                "No hay de qué, para eso estoy aquí. ¿Necesita ayuda con algo más?",
                "Es mi deber asistirle. Quedo a su disposición para cualquier otra consulta."
            ]
            return random.choice(thanks)
        
        # Problemas técnicos
        elif any(word in message_lower for word in ['error', 'bug', 'no funciona', 'problema técnico', 'falla']):
            return """🔧 **Problema técnico identificado**

Para poder asistirle de la mejor manera, le solicito amablemente que me proporcione los siguientes detalles:

• **Acción que intentaba realizar**
• **Mensaje de error específico** (si es posible, cópielo textualmente)
• **Momento en que comenzó el problema**
• **Dispositivo y navegador que está utilizando**

Con esta información podré brindarle una solución más precisa."""
        
        # Problemas de cuenta
        elif any(word in message_lower for word in ['cuenta', 'login', 'contraseña', 'verific', 'acceso', 'registro']):
            return """👤 **Asistencia con cuenta de usuario**

Para problemas relacionados con su cuenta, necesito que me indique:

• ¿Está teniendo dificultades para **iniciar sesión** o **recuperar su cuenta**?
• ¿Recibe algún **mensaje de error en particular**?
• ¿Ha **verificado su dirección de correo electrónico**? (le sugiero revisar también la carpeta de spam)

Agradeceré me proporcione más detalles para poder orientarle mejor."""
        
        # Reportes de usuarios
        elif any(word in message_lower for word in ['reportar', 'denunciar', 'usuario', 'comportamiento', 'abuso']):
            return """🚨 **Proceso de reporte**

Para procesar adecuadamente su reporte, necesito la siguiente información:

📋 **Datos requeridos:**
• **Nombre completo del usuario** (formato: @usuario#1234)
• **Descripción detallada del incidente**
• **Fecha y hora aproximada del suceso**
• **Canales donde ocurrió**
• **Capturas de pantalla** (si dispone de ellas)

Le ruego me proporcione estos datos para dar seguimiento a su reporte."""
        
        # Solicitudes de administrador
        elif any(word in message_lower for word in ['admin', 'administrador', 'humano', 'persona real', 'soporte humano']):
            return """📞 **Solicitud de asistencia administrativa**

He detectado que requiere comunicación con nuestro equipo administrativo. **Puede:**

1. Mencionar `@admin` en este canal
2. Utilizar el comando `!admin`
3. Esperar la revisión de su ticket por parte de nuestro staff

Mientras tanto, ¿podría proporcionarme más información sobre su consulta para agilizar el proceso?"""
        
        # Problemas de conexión/velocidad
        elif any(word in message_lower for word in ['lento', 'velocidad', 'carga', 'tarda', 'lag', 'delay']):
            return """🐌 **Incidencia de rendimiento**

Para optimizar la velocidad de conexión, le sugiero:

🔧 **Medidas correctivas:**
• Limpiar caché del navegador (Ctrl+Shift+Supr)
• Cerrar pestañas y aplicaciones innecesarias
• Reiniciar su router/módem
• Probar con conexión de datos móviles

¿Podría indicarme en qué función específica experimenta lentitud?"""
        
        # Preguntas con "cómo"
        elif any(word in message_lower for word in ['cómo', 'como']):
            if 'verific' in message_lower:
                return "**Para verificar su cuenta:**\n1. Revise su correo electrónico (incluyendo spam)\n2. Haga clic en el enlace de verificación\n3. Si no recibe el email en 10 minutos, utilice 'Reenviar email'\n4. Contacte con soporte si persiste el problema\n\n¿No está recibiendo el correo de verificación?"
            elif 'cambiar' in message_lower and 'contraseña' in message_lower:
                return "**Para cambiar su contraseña:**\n1. Acceda a Configuración → Seguridad\n2. Seleccione 'Cambiar contraseña'\n3. Siga las instrucciones proporcionadas\n4. Utilice una contraseña segura\n\n¿Tiene acceso a su cuenta actual?"
            elif 'reportar' in message_lower:
                return "**Para reportar un usuario:**\n1. Haga clic derecho sobre el usuario\n2. Seleccione 'Reportar usuario'\n3. Complete el formulario correspondiente\n4. Adjunte evidencias si las tiene\n\n¿Requiere asistencia con algún paso específico?"
            else:
                return "🤔 **Solicitud de instrucciones**\n\nComprendo que necesita orientación sobre algún procedimiento. ¿Podría especificar qué función o acción requiere explicación?"
        
        # Preguntas generales
        elif '?' in message:
            question_types = {
                'qué': "❓ **Consulta informativa**\n\nEstoy recopilando la información más actualizada para responderle. ¿Se trata de alguna función específica del servidor?",
                'por qué': "🔍 **Consulta causal**\n\nPara explicarle las razones detrás de esta situación, necesito más detalles sobre el problema específico.",
                'cuándo': "⏰ **Consulta temporal**\n\nLos tiempos pueden variar según diversos factores. ¿Podría proporcionarme más contexto sobre su situación?",
                'dónde': "📍 **Consulta de ubicación**\n\n¿Podría indicarme qué está buscando específicamente?"
            }
            
            for key, response in question_types.items():
                if key in message_lower:
                    return response
            
            return "🤖 **Consulta identificada**\n\nHe analizado su pregunta. Para brindarle la respuesta más adecuada, ¿podría proporcionar más contexto o detalles específicos?"
        
        # Mensajes cortos o vagos
        elif len(message.strip()) < 5:
            return "🤖 **Solicitud de información adicional**\n\nSu mensaje es bastante breve. ¿Podría describir su problema o consulta con mayor detalle?"
        
        # Respuesta por defecto para mensajes más largos
        else:
            detailed_responses = [
                "🔍 **Analizando su situación**\n\nPor su descripción, observo que requiere asistencia específica. ¿Podría proporcionarme:\n• La acción exacta que estaba realizando\n• El resultado que esperaba obtener\n• Lo que ocurrió en realidad\n\nEsta información me permitirá ofrecerle una solución precisa.",
                "💭 **Procesando su consulta**\n\nPara asistirle de manera efectiva, necesito comprender el contexto completo. ¿Podría indicarme:\n• Si esto ocurre consistentemente o es esporádico\n• Si afecta todas las funciones o solo alguna específica\n• Si se presenta en todos sus dispositivos o solo en uno\n\nEstos datos son cruciales para un diagnóstico adecuado.",
                "📋 **Comprendiendo su incidencia**\n\nPercibo que tiene una situación que requiere atención. Para brindarle la mejor asistencia, ¿podría facilitarme:\n• Su dispositivo (PC, móvil, etc.)\n• Navegador o aplicación que utiliza\n• Los pasos exactos que siguió\n\nCon esta información podré proporcionarle instrucciones específicas."
            ]
            return random.choice(detailed_responses)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Solo responder en canales de tickets
        if (isinstance(message.channel, discord.TextChannel) and 
            message.channel.name.startswith(('🎫-', '🚨-emergencia-'))):
            await self.handle_ticket_message(message)
    
    async def handle_ticket_message(self, message):
        """Manejar mensajes en tickets con IA profesional"""
        content = message.content
        
        # Ignorar comandos
        if content.startswith('!'):
            return
        
        # Si el mensaje menciona admin, dejar que el sistema de tickets lo maneje
        if any(word in content.lower() for word in ['@admin', 'administrador', 'ayuda humana']):
            return
        
        # Inicializar conversación si no existe
        if message.channel.id not in self.conversations:
            self.conversations[message.channel.id] = []
        
        # Mostrar que está pensando
        thinking_msg = await message.channel.send("🤖 *Infinity RB está procesando su mensaje...*")
        
        try:
            # Obtener contexto de la conversación (últimos 3 mensajes)
            context_messages = self.conversations[message.channel.id][-3:]
            context = " | ".join([f"{conv['user']}: {conv['message']}" for conv in context_messages])
            
            # Obtener respuesta de IA
            ai_response = await self.get_ai_response(content, context)
            
            # Guardar en historial de conversación
            self.conversations[message.channel.id].append({
                'user': message.author.display_name,
                'message': content,
                'bot_response': ai_response,
                'timestamp': datetime.now()
            })
            
            # Limitar historial a 10 mensajes para no usar mucha memoria
            if len(self.conversations[message.channel.id]) > 10:
                self.conversations[message.channel.id] = self.conversations[message.channel.id][-10:]
            
            # Crear embed con la respuesta profesional
            embed = discord.Embed(
                title="🤖 Infinity RB - Asistente Virtual",
                description=ai_response,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Footer limpio y profesional - SIN mención del modelo
            if self.gemini_available:
                embed.set_footer(text="Sistema de soporte automatizado • Estoy aquí para ayudarle")
            else:
                embed.set_footer(text="Sistema de soporte automatizado • Modo respuestas predefinidas")
            
            await thinking_msg.delete()
            response_msg = await message.channel.send(embed=embed)
            
            # Agregar reacciones útiles para feedback
            try:
                await response_msg.add_reaction('✅')  # Útil
                await response_msg.add_reaction('❌')  # No útil
                await response_msg.add_reaction('📞')  # Llamar admin
            except:
                pass  # Ignorar errores de permisos de reacciones
            
        except Exception as e:
            await thinking_msg.delete()
            error_embed = discord.Embed(
                title="❌ Error del Sistema",
                description="Lamentamos las molestias. He tenido un problema al procesar su mensaje. Por favor, intente de nuevo o solicite asistencia administrativa.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            print(f"❌ Error en handle_ticket_message: {e}")
    
    @commands.hybrid_command(name='ask', description='Consultar al asistente Infinity RB')
    async def ask_ai(self, ctx, *, pregunta: str):
        """Hacer una pregunta directa al asistente"""
        # Verificar que no sea un comando en un canal de tickets (para evitar duplicados)
        if (isinstance(ctx.channel, discord.TextChannel) and 
            ctx.channel.name.startswith(('🎫-', '🚨-emergencia-'))):
            await ctx.send("ℹ️ En tickets, puede escribir directamente sin usar `!ask`", ephemeral=True)
            return
        
        thinking_msg = await ctx.send("🤖 *Infinity RB está procesando su consulta...*")
        
        try:
            ai_response = await self.get_ai_response(pregunta, f"Consulta en #{ctx.channel.name}")
            
            embed = discord.Embed(
                title="🤖 Infinity RB - Asistente Virtual",
                description=ai_response,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Consulta de {ctx.author.display_name}")
            
            if not self.gemini_available:
                embed.add_field(name="💡 Nota", value="*Sistema de respuestas predefinidas activado*", inline=False)
            
            await thinking_msg.delete()
            await ctx.send(embed=embed)
            
        except Exception as e:
            await thinking_msg.delete()
            error_embed = discord.Embed(
                title="❌ Error del Sistema",
                description="No he podido procesar su consulta en este momento. Le ruego intente nuevamente.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
            print(f"❌ Error en ask_ai: {e}")
    
    @commands.hybrid_command(name='ai_status', description='Ver el estado del asistente Infinity RB')
    @commands.has_permissions(administrator=True)
    async def ai_status(self, ctx):
        """Mostrar el estado actual del asistente"""
        embed = discord.Embed(
            title="🤖 Estado del Sistema - Infinity RB",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Información del sistema
        if self.gemini_available:
            system_status = "✅ CONECTADO"
            system_details = "Sistema de IA completamente operativo"
        else:
            system_status = "🟡 MODO RESPUESTAS PREDEFINIDAS"
            system_details = "Sistema básico activo - Respuestas profesionales"
        
        embed.add_field(name="🔧 Estado del Sistema", value=system_status, inline=True)
        embed.add_field(name="📊 Funcionalidad", value=system_details, inline=True)
        
        # Estadísticas de conversaciones activas
        active_conversations = len(self.conversations)
        embed.add_field(name="💬 Tickets Activos", value=active_conversations, inline=True)
        
        # Información de uso
        embed.add_field(
            name="💡 Cómo utilizar el sistema", 
            value="• Escriba en cualquier ticket para asistencia automática\n• Utilice `!ask [consulta]` en otros canales\n• El sistema responderá de manera profesional y respetuosa",
            inline=False
        )
        
        if not self.gemini_available:
            embed.add_field(
                name="🚀 Para funcionalidad completa", 
                value="1. Obtenga API key en https://aistudio.google.com/\n2. Agregue `GEMINI_API_KEY=su_key` al archivo .env\n3. Reinicie el sistema",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AIAssistant(bot))