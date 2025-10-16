import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
import os
from datetime import datetime
import logging
import re

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
    
    @tasks.loop(minutes=3)
    async def check_lives(self):
        """Verifica cada 3 minutos si los usuarios están en vivo"""
        if not self.config["monitored_users"]:
            return
        
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        for username, user_data in self.config["monitored_users"].items():
            try:
                is_live = await self.check_tiktok_live_simple(username)
                
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
    
    async def check_tiktok_live_simple(self, username):
        """Método simple para verificar si está en vivo"""
        try:
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                },
                timeout=10
            ) as response:
                if response.status != 200:
                    return False
                
                html = await response.text()
                
                # Buscar patrones simples de live
                live_patterns = [
                    'isLive":true',
                    '"liveRoom":{',
                    'LIVE</span>',
                    'is_live":true',
                    'room_status":1'
                ]
                
                for pattern in live_patterns:
                    if pattern in html:
                        return True
                
                return False
                
        except asyncio.TimeoutError:
            print(f"⏰ Timeout verificando @{username}")
            return False
        except Exception as e:
            print(f"❌ Error en check simple @{username}: {str(e)}")
            return False
    
    async def verify_tiktok_user_simple(self, username):
        """Verificación simple de que el usuario existe"""
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
                    # Si contiene estos textos, probablemente el usuario no existe
                    error_indicators = [
                        "User doesn't exist",
                        "This page isn't available",
                        "Couldn't find this account",
                        "Page Not Found"
                    ]
                    
                    if any(error in html for error in error_indicators):
                        return False
                    
                    # Si llegamos aquí y la página carga, probablemente existe
                    return True
                elif response.status == 404:
                    return False
                else:
                    print(f"⚠️ Status code {response.status} para @{username}")
                    return False
                    
        except asyncio.TimeoutError:
            print(f"⏰ Timeout verificando usuario @{username}")
            return False
        except Exception as e:
            print(f"❌ Error verificando usuario @{username}: {str(e)}")
            return False
    
    async def send_live_alert(self, username, user_data):
        """Envía la alerta de live a los canales configurados"""
        embed = discord.Embed(
            title="🎥 **¡NUEVO DIRECTO EN TIKTOK!**",
            description=f"**@{username}** está en vivo",
            color=0x00f2ea,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Usuario",
            value=f"@{username}",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Enlace al Directo",
            value=f"[¡Haz click aquí para ver el directo!](https://www.tiktok.com/@{username}/live)",
            inline=False
        )
        
        embed.set_footer(text="Sistema de Alertas de TikTok")
        embed.set_thumbnail(url="https://i.imgur.com/7Y1f4yS.png")
        
        # Enviar a todos los canales configurados
        for guild_id, guild_data in self.config["guilds"].items():
            if "alert_channel" in guild_data:
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(int(guild_data["alert_channel"]))
                        if channel:
                            mention = ""
                            if "alert_role" in guild_data:
                                mention = f"<@&{guild_data['alert_role']}>"
                            
                            await channel.send(mention, embed=embed)
                            print(f"✅ Alerta enviada a {guild.name} - #{channel.name}")
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
        # Limpiar el username
        username = username.replace('@', '').strip().lower()
        
        # Validar formato de username
        if not re.match(r'^[a-zA-Z0-9._]+$', username):
            await ctx.send("❌ Nombre de usuario inválido. Solo se permiten letras, números, puntos y guiones bajosos.", ephemeral=True)
            return
        
        if username in self.config["monitored_users"]:
            await ctx.send("❌ Este usuario ya está siendo monitoreado.", ephemeral=True)
            return
        
        await ctx.defer()
        
        try:
            print(f"🔍 Verificando usuario: @{username}")
            user_exists = await self.verify_tiktok_user_simple(username)
            
            if not user_exists:
                await ctx.send(
                    "❌ No se pudo encontrar el usuario de TikTok. Verifica que:\n"
                    "• El nombre de usuario sea correcto\n"
                    "• La cuenta sea pública\n"
                    "• El usuario exista\n\n"
                    f"**URL probada:** https://www.tiktok.com/@{username}",
                    ephemeral=True
                )
                return
            
            # Agregar usuario
            self.config["monitored_users"][username] = {
                "added_by": ctx.author.id,
                "added_at": datetime.utcnow().isoformat(),
                "is_live": False,
                "guilds": [str(ctx.guild.id)],
                "last_checked": None
            }
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Usuario de TikTok Agregado",
                description=f"Ahora monitoreando: **@{username}**",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🔍 Estado",
                value="El sistema verificará automáticamente cada 3 minutos si está en vivo.",
                inline=False
            )
            
            embed.add_field(
                name="🔗 Perfil",
                value=f"[Ver perfil de TikTok](https://www.tiktok.com/@{username})",
                inline=False
            )
            
            await ctx.send(embed=embed)
            print(f"✅ Usuario @{username} agregado exitosamente")
            
        except Exception as e:
            error_msg = f"❌ Error al agregar el usuario: {str(e)}"
            print(error_msg)
            await ctx.send(error_msg, ephemeral=True)
    
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
        print(f"✅ Usuario @{username} removido")
    
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
            
            embed.add_field(
                name=f"@{username}",
                value=f"Estado: {status}\nAgregado por: {added_by_name}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_check", description="Verifica manualmente si un usuario está en vivo")
    @commands.has_permissions(administrator=True)
    async def check_tiktok_user(self, ctx, username: str):
        """Verifica manualmente si un usuario está en vivo"""
        username = username.replace('@', '').strip().lower()
        await ctx.defer()
        
        try:
            # Primero verificar que existe
            user_exists = await self.verify_tiktok_user_simple(username)
            
            if not user_exists:
                await ctx.send("❌ No se pudo encontrar el usuario de TikTok.", ephemeral=True)
                return
            
            # Luego verificar si está en vivo
            is_live = await self.check_tiktok_live_simple(username)
            
            embed = discord.Embed(
                title="🔍 Verificación de TikTok",
                color=0x00f2ea
            )
            embed.add_field(
                name="👤 Usuario",
                value=f"@{username}",
                inline=True
            )
            embed.add_field(
                name="🎥 Estado",
                value="🔴 **EN VIVO**" if is_live else "⚫ Offline",
                inline=True
            )
            embed.add_field(
                name="🔗 Enlaces",
                value=f"[Perfil](https://www.tiktok.com/@{username}) • [Live](https://www.tiktok.com/@{username}/live)",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error verificando usuario: {str(e)}", ephemeral=True)
    
    @commands.hybrid_command(name="tiktok_test", description="Prueba las alertas de TikTok")
    @commands.has_permissions(administrator=True)
    async def test_tiktok_alert(self, ctx, username: str = "example"):
        """Envía una alerta de prueba"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config["guilds"] or "alert_channel" not in self.config["guilds"][guild_id]:
            await ctx.send("❌ Primero configura el canal de alertas con `/tiktok_setup`", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎥 **¡PRUEBA DE ALERTA DE TIKTOK!**",
            description="Esta es una alerta de prueba del sistema de TikTok",
            color=0x00f2ea,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="👤 Usuario", value=f"@{username}", inline=True)
        embed.add_field(name="📊 Seguidores", value="1,000,000", inline=True)
        embed.add_field(
            name="🔗 Enlace al Directo",
            value=f"[¡Haz click aquí para ver el directo!](https://www.tiktok.com/@{username}/live)",
            inline=False
        )
        
        embed.set_footer(text="Sistema de Alertas de TikTok - PRUEBA")
        embed.set_thumbnail(url="https://i.imgur.com/7Y1f4yS.png")
        
        channel_id = self.config["guilds"][guild_id]["alert_channel"]
        channel = ctx.guild.get_channel(channel_id)
        
        if channel:
            await channel.send(embed=embed)
            await ctx.send("✅ Alerta de prueba enviada!", ephemeral=True)
        else:
            await ctx.send("❌ No se pudo encontrar el canal de alertas.", ephemeral=True)
    
    @commands.hybrid_command(name="tiktok_debug", description="Información de debug para TikTok")
    @commands.has_permissions(administrator=True)
    async def tiktok_debug(self, ctx, username: str):
        """Comando de debug para TikTok"""
        username = username.replace('@', '').strip().lower()
        await ctx.defer()
        
        try:
            # Probar conexión básica
            async with self.session.get(
                f"https://www.tiktok.com/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=10
            ) as response:
                status = response.status
                html_length = len(await response.text())
            
            embed = discord.Embed(
                title="🐛 Debug TikTok",
                color=0x00f2ea
            )
            embed.add_field(name="👤 Usuario", value=f"@{username}", inline=True)
            embed.add_field(name="📡 Status Code", value=status, inline=True)
            embed.add_field(name="📄 HTML Length", value=html_length, inline=True)
            embed.add_field(name="🔗 URL", value=f"https://www.tiktok.com/@{username}", inline=False)
            
            if status == 200:
                embed.add_field(name="✅ Página carga", value="Sí", inline=True)
            else:
                embed.add_field(name="❌ Página carga", value="No", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error en debug: {str(e)}", ephemeral=True)
    
    @check_lives.before_loop
    async def before_check_lives(self):
        """Espera a que el bot esté listo antes de empezar el loop"""
        await self.bot.wait_until_ready()
        # Inicializar session
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    @check_lives.error
    async def check_lives_error(self, error):
        """Maneja errores en el loop de verificación"""
        print(f"❌ Error en check_lives: {str(error)}")
        await asyncio.sleep(60)

async def setup(bot):
    await bot.add_cog(TikTokAlerts(bot))
