import os
from dotenv import load_dotenv

load_dotenv()

# Configuración del bot
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not BOT_TOKEN:
    raise ValueError("❌ No se encontró DISCORD_BOT_TOKEN en las variables de entorno")

# Configuración de roles (usa tus IDs)
ROLES = {
    "NORMAL": 1424194212064268410,  # Rol para comandos de utilidades/fun
    "ADMIN": 1424194293408727182,   # Rol para moderación, tickets, etc.
}

# Configuración de tickets
TICKET_CATEGORY_NAME = "🎫 TICKETS"
TICKET_COUNTER = 1  # NUEVO: Contador global de tickets

# Configuración de seguridad
MAX_JOINS_PER_MINUTE = 5
MAX_MENTIONS_PER_MESSAGE = 5

# Configuración de IA
AI_ENABLED = bool(GEMINI_API_KEY)
AI_MODEL = "gemini-1.5-pro-latest"  # Cambiado al modelo más reciente
AI_MAX_TOKENS = 500
AI_TEMPERATURE = 0.7

# Configuración de colores del bot
BOT_COLORS = {
    "primary": 0x6A0DAD,      # Morado principal
    "success": 0x00FF00,      # Verde para éxito
    "warning": 0xFFA500,      # Naranja para advertencias
    "error": 0xFF0000,        # Rojo para errores
    "info": 0x0099FF,         # Azul para información
}

def get_next_ticket_number():
    """Obtener el siguiente número de ticket"""
    global TICKET_COUNTER
    number = TICKET_COUNTER
    TICKET_COUNTER += 1
    return number

print("✅ Configuración cargada correctamente")
if AI_ENABLED:
    print("🤖 IA Google Gemini: ACTIVADA")
else:
    print("🤖 IA Google Gemini: DESACTIVADA (agrega GEMINI_API_KEY al .env)")