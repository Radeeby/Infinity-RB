import os
import sys

def check_environment():
    print("🔍 Verificando entorno...")
    
    # Verificar Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Verificar archivos
    required_files = ['main.py', 'config.py', 'requirements.txt']
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} encontrado")
        else:
            print(f"❌ {file} no encontrado")
            return False
    
    # Verificar carpeta cogs
    if os.path.exists('cogs') and os.path.isdir('cogs'):
        print("✅ Carpeta cogs encontrada")
        cog_files = [f for f in os.listdir('cogs') if f.endswith('.py') and f != '__init__.py']
        if cog_files:
            for cog in cog_files:
                print(f"✅ Cog encontrado: {cog}")
        else:
            print("❌ No se encontraron cogs en la carpeta cogs")
            return False
    else:
        print("❌ Carpeta cogs no encontrada")
        return False
    
    # Verificar .env
    if os.path.exists('.env'):
        print("✅ Archivo .env encontrado")
        with open('.env', 'r') as f:
            if 'DISCORD_BOT_TOKEN' in f.read():
                print("✅ DISCORD_BOT_TOKEN encontrado en .env")
            else:
                print("❌ DISCORD_BOT_TOKEN no encontrado en .env")
                return False
    else:
        print("❌ Archivo .env no encontrado")
        return False
    
    print("\n🎉 ¡Todo listo! Puedes ejecutar el bot con: python main.py")
    return True

if __name__ == "__main__":
    check_environment()