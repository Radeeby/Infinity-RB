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
    
    @tasks.loop(minutes=1)
    async def check_lives(self):
        """Verifica cada minuto si los usuarios están en vivo"""
        if not self.config["monitored_users"]:
            return
        
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        for username, user_data in self.config["monitored_users"].items():
            try:
                is_live = await self.check_tiktok_live(username)
                
                if is_live and not user_data.get("is_live", False):
                    # Usuario acaba de empezar directo
                    await self.send_live_alert(username, user_data)
                    user_data["is_live"] = True
                    self.save_config()
                    
                elif not is_live and user_data.get("is_live", False):
                    # Usuario terminó el directo
                    user_data["is_live"] = False
                    self.save_config()
                    
            except Exception as e:
                self.logger.error(f"Error checking {username}: {e}")
    
    async def check_tiktok_live(self, username):
        """Verifica si un usuario de TikTok está en vivo"""
        try:
            # Método 1: Usando API no oficial de TikTok
            async with self.session.get(
                f"https://www.tiktok.com/@{username}/live",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            ) as response:
                html = await response.text()
                
                # Buscar indicadores de live en el HTML
                live_indicators = [
                    "is_live": True,
                    "liveRoom",
                    "room_status\":1",
                    "is_live_stream"
                ]
                
                return any(indicator in html for indicator in live_indicators)
                
        except Exception as e:
            self.logger.error(f"Error checking TikTok live for {username}: {e}")
            return False
    
    async def get_tiktok_user_info(self, username):
        """Obtiene información del usuario de TikTok"""
        try:
            async with self.session.get(
                f"https://www.tiktok.com/node/share/user/@{username}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("userInfo", {})
                return {}
        except:
            return {}
    
    async def send_live_alert(self, username, user_data):
        """Envía la alerta de live a los canales configurados"""
        user_info = await self.get_tiktok_user_info(username)
        
        embed = discord.Embed(
            title="🎥 **¡NUEVO DIRECTO EN TIKTOK!**",
            color=0x00f2ea,  # Color de TikTok
            timestamp=datetime.utcnow()
        )
        
        # Información del usuario
        if user_info:
            embed.set_author(
                name=user_info.get("user", {}).get("nickname", username),
                icon_url=user_info.get("user", {}).get("avatarThumb", "")
            )
            embed.add_field(
                name="👤 Usuario",
                value=f"@{username}",
                inline=True
            )
            embed.add_field(
                name="📊 Seguidores",
                value=f"{user_info.get('user', {}).get('followerCount', 'N/A'):,}",
                inline=True
            )
        else:
            embed.add_field(
                name="👤 Usuario",
                value=f"@{username}",
                inline=False
            )
        
        # Enlace al directo
        embed.add_field(
            name="🔗 Enlace al Directo",
            value=f"[¡Haz click aquí para ver el directo!](https://www.tiktok.com/@{username}/live)",
            inline=False
        )
        
        embed.set_footer(text="Sistema de Alertas de TikTok")
        embed.set_thumbnail(url="https://i.imgur.com/7Y1f4yS.png")  # Logo TikTok
        
        # Enviar a todos los canales configurados
        for guild_id, guild_data in self.config["guilds"].items():
            if "alert_channel" in guild_data:
                try:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(int(guild_data["alert_channel"]))
                        if channel:
                            # Mención de rol si está configurado
                            mention = ""
                            if "alert_role" in guild_data:
                                mention = f"<@&{guild_data['alert_role']}>"
                            
                            await channel.send(mention, embed=embed)
                except Exception as e:
                    self.logger.error(f"Error sending alert to guild {guild_id}: {e}")
    
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
        username = username.replace('@', '').strip()
        
        if username in self.config["monitored_users"]:
            await ctx.send("❌ Este usuario ya está siendo monitoreado.", ephemeral=True)
            return
        
        # Verificar que el usuario existe
        try:
            user_info = await self.get_tiktok_user_info(username)
            if not user_info:
                await ctx.send("❌ No se pudo encontrar el usuario de TikTok.", ephemeral=True)
                return
        except:
            await ctx.send("❌ Error al verificar el usuario de TikTok.", ephemeral=True)
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
        embed.add_field(name="👤 Nombre", value=user_info.get("user", {}).get("nickname", "N/A"), inline=True)
        embed.add_field(name="📊 Seguidores", value=f"{user_info.get('user', {}).get('followerCount', 'N/A'):,}", inline=True)
        embed.set_thumbnail(url=user_info.get("user", {}).get("avatarThumb", ""))
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_remove", description="Remueve un usuario de TikTok del monitoreo")
    @commands.has_permissions(administrator=True)
    async def remove_tiktok_user(self, ctx, username: str):
        """Remueve un usuario de TikTok de la lista de monitoreo"""
        username = username.replace('@', '').strip()
        
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
            
            embed.add_field(
                name=f"@{username}",
                value=f"Estado: {status}\nAgregado por: {added_by_name}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="tiktok_test", description="Prueba las alertas de TikTok")
    @commands.has_permissions(administrator=True)
    async def test_tiktok_alert(self, ctx, username: str = "example"):
        """Envía una alerta de prueba"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config["guilds"] or "alert_channel" not in self.config["guilds"][guild_id]:
            await ctx.send("❌ Primero configura el canal de alertas con `/tiktok_setup`", ephemeral=True)
            return
        
        # Crear embed de prueba
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
    
    @commands.hybrid_command(name="tiktok_role", description="Configura un rol para mencionar en las alertas")
    @commands.has_permissions(administrator=True)
    async def set_alert_role(self, ctx, role: discord.Role):
        """Configura un rol para ser mencionado en las alertas"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config["guilds"]:
            self.config["guilds"][guild_id] = {}
        
        self.config["guilds"][guild_id]["alert_role"] = role.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Rol de Alertas Configurado",
            description=f"El rol {role.mention} será mencionado en las alertas de TikTok",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @check_lives.before_loop
    async def before_check_lives(self):
        """Espera a que el bot esté listo antes de empezar el loop"""
        await self.bot.wait_until_ready()
    
    @check_lives.error
    async def check_lives_error(self, error):
        """Maneja errores en el loop de verificación"""
        self.logger.error(f"Error in check_lives loop: {error}")
        await asyncio.sleep(60)  # Esperar antes de reintentar

async def setup(bot):
    await bot.add_cog(TikTokAlerts(bot))
