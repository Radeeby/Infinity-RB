import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta, timezone
import re
import config

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_times = []
        self.raid_mode = False
        self.suspicious_joins = []
        
        # Patrones de nombres de bots maliciosos conocidos
        self.malicious_bot_patterns = [
            r'shappire', r'sapphire', r'shapire', r'shappire-bot', r'shappirebot',
            r'nuke', r'raid', r'crash', r'destroy', r'annihilator',
            r'blood', r'killer', r'murder', r'destroyer', r'wizard',
            r'ghost', r'shadow', r'phantom', r'stealth', r'invisible',
            r'vortex', r'storm', r'hurricane', r'tsunami', r'earthquake',
            r'venom', r'poison', r'toxic', r'acid', r'plague',
            r'chaos', r'anarchy', r'hysteria', r'panic', r'mayhem',
            r'cyber', r'hack', r'crack', r'exploit', r'virus',
            r'demon', r'devil', r'satan', r'hell', r'inferno',
            r'omega', r'alpha', r'sigma', r'ultima', r'extreme',
            r'null', r'void', r'empty', r'zero', r'voided',
            r'cipher', r'code', r'script', r'auto', r'botter'
        ]
        
        # Patrones de nombres con muchos números
        self.number_patterns = [
            r'[0-9]{4,}',  # 4 o más números consecutivos
            r'.*[0-9]{3,}.*[0-9]{3,}.*',  # Múltiples grupos de números
        ]
        
        # Usuarios verificados como seguros (staff, etc.)
        self.verified_users = set()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Detección avanzada de raids y bots maliciosos"""
        if member.bot:
            await self.handle_bot_join(member)
            return
            
        await self.handle_user_join(member)

    async def handle_bot_join(self, member):
        """Manejar joins de bots"""
        guild = member.guild
        
        # Verificar si el bot fue añadido por un administrador
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                # Bot añadido por administrador - considerado seguro
                if entry.user.guild_permissions.administrator:
                    print(f"✅ Bot {member.name} añadido por administrador: {entry.user.name}")
                    return
                break
        
        # Bot no autorizado detectado
        await self.take_action_against_bot(member)

    async def handle_user_join(self, member):
        """Manejar joins de usuarios normales"""
        guild = member.guild
        now = datetime.now(timezone.utc)
        
        # Detección de raid por joins masivos
        self.join_times.append(now)
        
        # Limpiar joins antiguos (últimos 60 segundos)
        self.join_times = [join_time for join_time in self.join_times 
                          if now - join_time < timedelta(seconds=60)]
        
        # Si hay más de 8 joins en 60 segundos, activar modo raid
        if len(self.join_times) > 8 and not self.raid_mode:
            await self.activate_raid_mode(guild, "Joins masivos detectados")
        
        # Verificar cuenta sospechosa
        is_suspicious, reasons = await self.check_suspicious_account(member)
        
        if is_suspicious:
            self.suspicious_joins.append({
                'member': member,
                'reasons': reasons,
                'timestamp': now
            })
            
            # Si hay más de 3 joins sospechosos en 2 minutos, activar medidas
            recent_suspicious = [s for s in self.suspicious_joins 
                               if now - s['timestamp'] < timedelta(minutes=2)]
            
            if len(recent_suspicious) > 3 and not self.raid_mode:
                await self.activate_raid_mode(guild, "Múltiples joins sospechosos")
            
            await self.log_suspicious_account(member, reasons)

    async def check_suspicious_account(self, member):
        """Verificar si una cuenta es sospechosa"""
        suspicious_signs = []
        
        # 1. Cuenta recién creada (menos de 2 días)
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        if account_age < 2:
            suspicious_signs.append(f"Cuenta muy nueva ({account_age} días)")
        
        # 2. Sin avatar personalizado
        if not member.avatar:
            suspicious_signs.append("Sin avatar personalizado")
        
        # 3. Nombre sospechoso (patrones de bots maliciosos)
        display_name_lower = member.display_name.lower()
        for pattern in self.malicious_bot_patterns:
            if re.search(pattern, display_name_lower):
                suspicious_signs.append("Nombre coincide con patrones de bots maliciosos")
                break
        
        # 4. Nombre con muchos números
        for pattern in self.number_patterns:
            if re.search(pattern, member.display_name):
                suspicious_signs.append("Nombre con muchos números")
                break
        
        # 5. Nombre muy genérico o aleatorio
        if self.is_generic_name(member.display_name):
            suspicious_signs.append("Nombre genérico/aleatorio")
        
        # 6. Sin banner de perfil
        if not member.banner:
            suspicious_signs.append("Sin banner de perfil")
        
        return len(suspicious_signs) >= 2, suspicious_signs

    def is_generic_name(self, name):
        """Detectar nombres genéricos o aleatorios"""
        generic_patterns = [
            r'^[a-z]+[0-9]+$',  # palabranúmeros
            r'^[0-9]+[a-z]+$',  # númerospalabra
            r'^[a-z]+\.[a-z]+$',  # palabra.palabra
            r'^[a-z]+_[a-z]+$',  # palabra_palabra
        ]
        
        name_lower = name.lower()
        for pattern in generic_patterns:
            if re.match(pattern, name_lower):
                return True
        
        # Números excesivos en el nombre
        digit_count = sum(c.isdigit() for c in name)
        if digit_count > len(name) * 0.4:  # Más del 40% son números
            return True
            
        return False

    async def take_action_against_bot(self, member):
        """Tomar acción contra bots no autorizados"""
        try:
            # 1. Expulsar el bot
            await member.kick(reason="Bot no autorizado detectado")
            
            # 2. Log la acción
            await self.log_security_incident(
                member.guild,
                "🚫 BOT NO AUTORIZADO EXPULSADO",
                f"**Bot:** {member.mention} (`{member.name}`)\n"
                f"**ID:** {member.id}\n"
                f"**Razón:** Bot añadido sin autorización administrativa",
                discord.Color.red()
            )
            
            # 3. Notificar a administradores
            await self.notify_admins(
                member.guild,
                f"🚨 **Bot no autorizado expulsado**\n"
                f"Se ha expulsado automáticamente al bot {member.mention} "
                f"por no tener autorización administrativa."
            )
            
        except discord.Forbidden:
            await self.log_security_incident(
                member.guild,
                "❌ ERROR AL EXPULSAR BOT",
                f"No tengo permisos para expulsar al bot {member.mention}",
                discord.Color.orange()
            )

    async def activate_raid_mode(self, guild, reason):
        """Activar modo raid con medidas de seguridad"""
        if self.raid_mode:
            return
            
        self.raid_mode = True
        
        # Buscar o crear canal de logs
        log_channel = await self.get_or_create_log_channel(guild)
        
        # Aplicar medidas de seguridad
        security_measures = []
        
        try:
            # 1. Desactivar invites temporalmente
            for channel in guild.text_channels:
                if channel.permissions_for(guild.default_role).send_messages:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                    security_measures.append(f"🔒 {channel.mention}")
            
            # 2. Activar verificación de nivel medio
            original_verification = guild.verification_level
            if guild.verification_level.value < 2:  # Menos que MEDIUM
                await guild.edit(verification_level=discord.VerificationLevel.medium)
                security_measures.append("🛡️ Verificación nivel MEDIUM")
            
            # 3. Desactivar creación de invites
            await guild.edit(invites_disabled=True)
            security_measures.append("🚫 Invites desactivados")
            
            embed = discord.Embed(
                title="🚨 MODO RAID ACTIVADO",
                description=f"**Razón:** {reason}\n"
                          f"**Medidas aplicadas:**\n" + "\n".join(security_measures),
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="📊 Estadísticas",
                value=f"**Joins recientes:** {len(self.join_times)}\n"
                      f"**Cuentas sospechosas:** {len(self.suspicious_joins)}",
                inline=True
            )
            
            await log_channel.send(embed=embed)
            
            # Notificar a todos los administradores
            await self.notify_admins(
                guild,
                f"🚨 **MODO RAID ACTIVADO**\n"
                f"**Razón:** {reason}\n"
                f"El servidor está bajo medidas de seguridad automáticas."
            )
            
            # Programar desactivación automática después de 15 minutos
            await asyncio.sleep(900)  # 15 minutos
            await self.deactivate_raid_mode(guild)
            
        except Exception as e:
            await log_channel.send(f"❌ Error activando modo raid: {str(e)}")

    async def deactivate_raid_mode(self, guild):
        """Desactivar modo raid"""
        if not self.raid_mode:
            return
            
        self.raid_mode = False
        
        log_channel = await self.get_or_create_log_channel(guild)
        
        try:
            # Reactivar permisos de canales
            for channel in guild.text_channels:
                if not channel.permissions_for(guild.default_role).send_messages:
                    await channel.set_permissions(guild.default_role, send_messages=True)
            
            # Reactivar invites
            await guild.edit(invites_disabled=False)
            
            embed = discord.Embed(
                title="✅ MODO RAID DESACTIVADO",
                description="Todas las medidas de seguridad han sido levantadas.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            await log_channel.send(embed=embed)
            
            # Limpiar listas de tracking
            self.join_times.clear()
            self.suspicious_joins.clear()
            
        except Exception as e:
            await log_channel.send(f"❌ Error desactivando modo raid: {str(e)}")

    async def log_suspicious_account(self, member, reasons):
        """Registrar cuenta sospechosa"""
        log_channel = await self.get_or_create_log_channel(member.guild)
        
        embed = discord.Embed(
            title="⚠️ Cuenta Sospechosa Detectada",
            description=f"**Usuario:** {member.mention}\n**ID:** {member.id}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🔍 Señales de alerta",
            value="\n".join([f"• {reason}" for reason in reasons]),
            inline=False
        )
        
        embed.add_field(
            name="📅 Información de cuenta",
            value=f"**Creada:** {member.created_at.strftime('%d/%m/%Y %H:%M')}\n"
                  f"**Edad:** {(datetime.now(timezone.utc) - member.created_at).days} días",
            inline=True
        )
        
        await log_channel.send(embed=embed)

    async def get_or_create_log_channel(self, guild):
        """Obtener o crear canal de logs de seguridad"""
        log_channel = discord.utils.get(guild.text_channels, name="🔒security-logs")
        
        if not log_channel:
            # Crear canal de logs si no existe
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Agregar permisos para administradores
            admin_role = guild.get_role(config.ROLES["ADMIN"])
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            log_channel = await guild.create_text_channel(
                "🔒security-logs",
                overwrites=overwrites,
                reason="Canal de logs de seguridad automático"
            )
        
        return log_channel

    async def log_security_incident(self, guild, title, description, color):
        """Registrar incidente de seguridad"""
        log_channel = await self.get_or_create_log_channel(guild)
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        await log_channel.send(embed=embed)

    async def notify_admins(self, guild, message):
        """Notificar a los administradores"""
        admin_role = guild.get_role(config.ROLES["ADMIN"])
        if admin_role:
            # Buscar un canal donde enviar la notificación
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(f"{admin_role.mention} {message}")
                        break
                    except:
                        continue

    @commands.Cog.listener()
    async def on_message(self, message):
        """Protección contra spam y contenido malicioso"""
        if message.author.bot:
            return
        
        # Anti spam de menciones
        if len(message.mentions) > 5:
            await self.handle_mention_spam(message)
            return
        
        # Anti enlaces sospechosos
        if await self.contains_suspicious_links(message.content):
            await self.handle_suspicious_links(message)
            return
        
        # Anti spam de mensajes rápidos
        await self.check_message_spam(message)

    async def handle_mention_spam(self, message):
        """Manejar spam de menciones"""
        try:
            await message.delete()
            
            warning_msg = await message.channel.send(
                f"{message.author.mention} ¡No hagas spam de menciones! "
                f"(Máximo 5 menciones por mensaje)"
            )
            
            # Log la acción
            await self.log_security_incident(
                message.guild,
                "🚫 Spam de Menciones Bloqueado",
                f"**Usuario:** {message.author.mention}\n"
                f"**Canal:** {message.channel.mention}\n"
                f"**Menciones:** {len(message.mentions)}",
                discord.Color.orange()
            )
            
            await asyncio.sleep(10)
            await warning_msg.delete()
            
        except discord.Forbidden:
            pass

    async def contains_suspicious_links(self, content):
        """Detectar enlaces sospechosos"""
        suspicious_domains = [
            'discord.gift', 'discord.com/gifts', 'discordapp.com/gifts',
            'nitro.gift', 'free-nitro.xyz', 'steamcommunity.com/giveaway',
            'steamgifts.com', 'free-steam.com'
        ]
        
        for domain in suspicious_domains:
            if domain in content.lower():
                return True
        return False

    async def handle_suspicious_links(self, message):
        """Manejar enlaces sospechosos"""
        try:
            await message.delete()
            
            warning_msg = await message.channel.send(
                f"{message.author.mention} ¡Los enlaces de regalos falsos no están permitidos!"
            )
            
            await self.log_security_incident(
                message.guild,
                "🔗 Enlace Sospechoso Eliminado",
                f"**Usuario:** {message.author.mention}\n"
                f"**Canal:** {message.channel.mention}\n"
                f"**Contenido:** {message.content[:100]}...",
                discord.Color.orange()
            )
            
            await asyncio.sleep(10)
            await warning_msg.delete()
            
        except discord.Forbidden:
            pass

    async def check_message_spam(self, message):
        """Verificar spam de mensajes rápidos"""
        # Esta función puede expandirse para tracking de spam más avanzado
        pass

    # COMANDOS DE ADMINISTRACIÓN

    @commands.hybrid_command(name='raid_mode', description='Activar/desactivar modo raid manualmente')
    @commands.has_permissions(administrator=True)
    async def raid_mode(self, ctx, action: str):
        """Control manual del modo raid"""
        if action.lower() in ['activar', 'on', 'enable']:
            await self.activate_raid_mode(ctx.guild, "Activado manualmente por administrador")
            await ctx.send("✅ Modo raid activado manualmente")
        else:
            await self.deactivate_raid_mode(ctx.guild)
            await ctx.send("✅ Modo raid desactivado")

    @commands.hybrid_command(name='security_status', description='Estado del sistema de seguridad')
    @commands.has_permissions(administrator=True)
    async def security_status(self, ctx):
        """Mostrar estado del sistema de seguridad"""
        embed = discord.Embed(
            title="🛡️ Estado del Sistema de Seguridad",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🚨 Modo Raid",
            value="**ACTIVADO**" if self.raid_mode else "**Desactivado**",
            inline=True
        )
        
        embed.add_field(
            name="📊 Joins Recientes",
            value=f"**Último minuto:** {len(self.join_times)}",
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Sospechosos",
            value=f"**Registrados:** {len(self.suspicious_joins)}",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Funciones Activas",
            value="• Anti-raid automático\n• Detección de bots\n• Anti-mention spam\n• Protección de enlaces",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='scan_members', description='Escanear miembros recientes en busca de cuentas sospechosas')
    @commands.has_permissions(administrator=True)
    async def scan_members(self, ctx, hours: int = 24):
        """Escanear miembros recientes"""
        scan_msg = await ctx.send("🔍 Escaneando miembros recientes...")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        suspicious_count = 0
        
        async with ctx.typing():
            for member in ctx.guild.members:
                if member.joined_at and member.joined_at > cutoff_time:
                    is_suspicious, reasons = await self.check_suspicious_account(member)
                    if is_suspicious:
                        suspicious_count += 1
            
            embed = discord.Embed(
                title="🔍 Escaneo de Miembros Completado",
                description=f"**Período:** Últimas {hours} horas\n"
                          f"**Miembros escaneados:** {len([m for m in ctx.guild.members if m.joined_at and m.joined_at > cutoff_time])}\n"
                          f"**Cuentas sospechosas:** {suspicious_count}",
                color=discord.Color.orange() if suspicious_count > 0 else discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            
            if suspicious_count > 0:
                embed.add_field(
                    name="💡 Recomendación",
                    value="Considera revisar manualmente las cuentas sospechosas "
                          "y activar verificación de nivel medio si es necesario.",
                    inline=False
                )
        
        await scan_msg.delete()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Security(bot))