import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import os
from datetime import datetime
import logging

class TikTokAlerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'data/tiktok_alerts.json'
        self.config = self.load_config()
        self.session = None
        self.check_lives.start()
        self.logger = logging.getLogger('tiktok_alerts')
    
    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"guilds": {}, "monitored_users": {}}
    
    def save_config(self):
        """Guarda la configuración en el archivo JSON"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def cog_unload(self):
        """Limpia recursos cuando el cog se descarga"""
        self.check_lives.cancel()
        if self.session:
            asyncio.create_task(self.session.close())
    
    @tasks.loop(minutes=5)
    async def check_lives(self):
        """Verifica cada 5 minutos si los usuarios están en vivo"""
        if not self.config["monitored_users"]:
            return
        
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        for username, user_data in self.config["monitored_users"].items():
            try:
                is_live = await self.check_tiktok_live_alternative(username)
                
                if is_live and not user_data.get("is_live", False):
                    # Usuario acaba de empezar directo
                    await self.send_live_alert(username, user_data)
                    user_data["is_live"] = True
                    self.save_config()
                    print(f"🔴 LIVE DETECTADO: @{username}")
                    
                elif not is_live and user_data.get("is_live", False):
                    # Usuario terminó el directo
                    user_data["is_live"] = False
                    self.save_config()
                    print(f"⚫ LIVE TERMINADO: @{username}")
                    
            except Exception as e:
                print(f"❌ Error checking {username}: {str(e)}")
    
    async def check_tiktok_live_alternative(self, username):
        """Método alternativo usando diferentes enfoques"""
        try:
            # Método 1: Usar TikTok API no oficial (si está disponible)
            live_status = await self.check_via_unofficial_api(username)
            if live_status is not None:
                return live_status
            
            # Método 2: Verificar página con headers móviles
            live_status = await self.check_via_mobile_headers(username)
            if live_status is not None:
                return live_status
                
            # Método 3: Verificación básica
            return await self.check_via_basic_request(username)
            
        except Exception as e:
            print(f"❌ Error en método alternativo para @{username}: {str(e)}")
            return False
    
    async def check_via_unofficial_api(self, username):
        """Intentar usar API no oficial de TikTok"""
        try:
            # Este endpoint a veces funciona
            async with self.session.get(
                f"https://www.tiktok.com/node/share/user/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and 'userInfo' in data:
                        user_info = data['userInfo']['user']
                        return user_info.get('isLive', False)
            return None
        except:
            return None
    
    async def check_via_mobile_headers(self, username):
        """Usar headers de móvil para evitar bloqueos"""
        try:
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-us",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    # Buscar indicadores de live en HTML móvil
                    live_indicators = [
                        'isLive":true',
                        '"liveRoom"',
                        'LIVE</span>',
                        'room_status":1'
                    ]
                    return any(indicator in html for indicator in live_indicators)
            return None
        except:
            return None
    
    async def check_via_basic_request(self, username):
        """Método básico de verificación"""
        try:
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return 'LIVE</span>' in html or 'isLive":true' in html
                return False
        except:
            return False
    
    async def verify_user_exists(self, username):
        """Verificar si el usuario existe usando múltiples métodos"""
        try:
            # Método 1: Verificación directa
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    # Si contiene estos textos, el usuario no existe
                    if any(error in html for error in ["User doesn't exist", "This page isn't available", "Couldn't find this account"]):
                        return False
                    return True
                elif response.status == 404:
                    return False
                else:
                    # Si el status no es 200 o 404, intentar otro método
                    return await self.verify_user_alternative(username)
                    
        except Exception as e:
            print(f"❌ Error en verificación principal: {str(e)}")
            return await self.verify_user_alternative(username)
    
    async def verify_user_alternative(self, username):
        """Método alternativo para verificar usuario"""
        try:
            # Usar un servicio de terceros o método diferente
            async with self.session.get(
                f"https://www.tiktok.com/node/share/user/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                },
                timeout=10
            ) as response:
                return response.status == 200
        except:
            return False
    
    async def send_live_alert(self, username, user_data):
        """Envía la alerta de live"""
        embed = discord.Embed(
            title="🎥 **¡NUEVO DIRECTO EN TIKTOK!**",
            description=f"**@{username}** está en vivo",
            color=0x00f2ea,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="👤 Usuario", value=f"@{username}", inline=True)
        embed.add_field(name="🔗 Enlace al Directo", value=f"[¡Ver directo!](https://www.tiktok.com/@{username}/live)", inline=False)
        embed.set_footer(text="Sistema de Alertas de TikTok")
        embed.set_thumbnail(url="https://i.imgur.com/7Y1f4yS.png")
        
        for guild_id, guild_data in self.config["guilds"].items():
            if "alert_channel" in guild_data:
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(int(guild_data["alert_channel"]))
                        if channel:
                            mention = f"<@&{guild_data['alert_role']}>" if "alert_role" in guild_data else ""
                            await channel.send(mention, embed=embed)
                            print(f"✅ Alerta enviada a {guild.name}")
                except Exception as e:
                    print(f"❌ Error enviando alerta: {str(e)}")
    
    @commands.hybrid_command(name="tiktok_setup", description="Configura el canal de alertas de TikTok")
    @commands.has_permissions(administrator=True)
    async def setup_tiktok(self, ctx, channel: discord.TextChannel):
        """Configura el canal para las alertas de TikTok"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config["guilds"]:
            self.config["guilds"][guild_id] = {}
        
        self.config["guilds"][guild_id]["alert_channel"] = channel.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Configuración de TikTok Completada",
            description=f"Las alertas de TikTok se enviarán en {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_add", description="Agrega un usuario de TikTok para monitorear")
    @commands.has_permissions(administrator=True)
    async def add_tiktok_user(self, ctx, username: str):
        """Agrega un usuario de TikTok a la lista de monitoreo"""
        username = username.replace('@', '').strip().lower()
        
        if username in self.config["monitored_users"]:
            await ctx.send("❌ Este usuario ya está siendo monitoreado.", ephemeral=True)
            return
        
        await ctx.defer()
        
        try:
            print(f"🔍 Verificando usuario: @{username}")
            
            # Verificar usando múltiples métodos
            user_exists = await self.verify_user_exists(username)
            
            if not user_exists:
                # Intentar método más permisivo
                user_exists = await self.verify_by_direct_access(username)
            
            if not user_exists:
                await ctx.send(
                    f"❌ No se pudo verificar el usuario @{username}.\n\n"
                    "**Posibles causas:**\n"
                    "• El usuario no existe\n"
                    "• La cuenta es privada\n"
                    "• TikTok está bloqueando las verificaciones\n"
                    "• Problemas temporales de conexión\n\n"
                    "**Solución:**\n"
                    "1. Verifica manualmente que https://www.tiktok.com/@{username} funciona\n"
                    "2. Espera unos minutos e intenta nuevamente\n"
                    "3. Prueba con otro usuario",
                    ephemeral=True
                )
                return
            
            # Agregar usuario
            self.config["monitored_users"][username] = {
                "added_by": ctx.author.id,
                "added_at": datetime.utcnow().isoformat(),
                "is_live": False,
                "guilds": [str(ctx.guild.id)]
            }
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Usuario de TikTok Agregado",
                description=f"Ahora monitoreando: **@{username}**",
                color=discord.Color.green()
            )
            embed.add_field(name="🔍 Monitoreo", value="Se verificará cada 5 minutos", inline=False)
            embed.add_field(name="🔗 Perfil", value=f"[Abrir en TikTok](https://www.tiktok.com/@{username})", inline=False)
            
            await ctx.send(embed=embed)
            print(f"✅ Usuario @{username} agregado exitosamente")
            
        except Exception as e:
            error_msg = f"❌ Error inesperado: {str(e)}"
            print(error_msg)
            await ctx.send(error_msg, ephemeral=True)
    
    async def verify_by_direct_access(self, username):
        """Método más permisivo - asume que el usuario existe si no hay error claro"""
        try:
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=10
            ) as response:
                # Si la página carga sin errores claros, asumimos que existe
                return response.status == 200
        except:
            return False
    
    @commands.hybrid_command(name="tiktok_force_add", description="Agrega un usuario sin verificación (para testing)")
    @commands.has_permissions(administrator=True)
    async def force_add_tiktok_user(self, ctx, username: str):
        """Agrega un usuario sin verificación (útil para testing)"""
        username = username.replace('@', '').strip().lower()
        
        if username in self.config["monitored_users"]:
            await ctx.send("❌ Este usuario ya está siendo monitoreado.", ephemeral=True)
            return
        
        self.config["monitored_users"][username] = {
            "added_by": ctx.author.id,
            "added_at": datetime.utcnow().isoformat(),
            "is_live": False,
            "guilds": [str(ctx.guild.id)],
            "forced": True  # Marcar como agregado forzadamente
        }
        self.save_config()
        
        embed = discord.Embed(
            title="⚠️ Usuario Agregado (Sin Verificación)",
            description=f"Monitoreando: **@{username}**\n\n*Este usuario fue agregado sin verificación. El sistema intentará detectar lives.*",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        print(f"⚠️ Usuario @{username} agregado forzadamente")
    
    @commands.hybrid_command(name="tiktok_remove", description="Remueve un usuario de TikTok del monitoreo")
    @commands.has_permissions(administrator=True)
    async def remove_tiktok_user(self, ctx, username: str):
        """Remueve un usuario de TikTok de la lista de monitoreo"""
        username = username.replace('@', '').strip().lower()
        
        if username not in self.config["monitored_users"]:
            await ctx.send("❌ Este usuario no está siendo monitoreado.", ephemeral=True)
            return
        
        del self.config["monitored_users"][username]
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Usuario de TikTok Removido",
            description=f"Ya no se monitorea: **@{username}**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_list", description="Lista todos los usuarios de TikTok monitoreados")
    async def list_tiktok_users(self, ctx):
        """Muestra la lista de usuarios de TikTok siendo monitoreados"""
        if not self.config["monitored_users"]:
            await ctx.send("📝 No hay usuarios de TikTok siendo monitoreados.")
            return
        
        embed = discord.Embed(
            title="📱 Usuarios de TikTok Monitoreados",
            color=0x00f2ea
        )
        
        for username, data in self.config["monitored_users"].items():
            status = "🔴 **EN VIVO**" if data.get("is_live", False) else "⚫ Offline"
            added_by = self.bot.get_user(data["added_by"])
            added_by_name = added_by.display_name if added_by else "Usuario desconocido"
            forced = " ⚠️ (Forzado)" if data.get("forced", False) else ""
            
            embed.add_field(
                name=f"@{username}{forced}",
                value=f"Estado: {status}\nAgregado por: {added_by_name}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_status", description="Verifica el estado del sistema de TikTok")
    @commands.has_permissions(administrator=True)
    async def tiktok_status(self, ctx):
        """Muestra el estado del sistema de TikTok"""
        embed = discord.Embed(
            title="📊 Estado del Sistema TikTok",
            color=0x00f2ea
        )
        
        embed.add_field(
            name="👥 Usuarios Monitoreados",
            value=len(self.config["monitored_users"]),
            inline=True
        )
        
        embed.add_field(
            name="🔄 Intervalo de Verificación",
            value="5 minutos",
            inline=True
        )
        
        embed.add_field(
            name="📡 Estado del Servicio",
            value="✅ Activo" if self.check_lives.is_running() else "❌ Inactivo",
            inline=True
        )
        
        # Contar usuarios en vivo
        live_count = sum(1 for user in self.config["monitored_users"].values() if user.get("is_live", False))
        embed.add_field(
            name="🎥 Usuarios en Vivo",
            value=live_count,
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @check_lives.before_loop
    async def before_check_lives(self):
        """Espera a que el bot esté listo antes de empezar el loop"""
        await self.bot.wait_until_ready()
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    @check_lives.error
    async def check_lives_error(self, error):
        """Maneja errores en el loop de verificación"""
        print(f"❌ Error en check_lives: {str(error)}")
        await asyncio.sleep(60)

async def setup(bot):
    await bot.add_cog(TikTokAlerts(bot))
