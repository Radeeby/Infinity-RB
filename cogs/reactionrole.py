import discord
from discord.ext import commands
import json
import os
from typing import Dict, List

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_file = 'data/reaction_roles.json'
        self.reaction_roles = self.load_reaction_roles()
    
    def load_reaction_roles(self):
        """Carga los reaction roles desde el archivo JSON"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.reaction_roles_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_reaction_roles(self):
        """Guarda los reaction roles en el archivo JSON"""
        with open(self.reaction_roles_file, 'w') as f:
            json.dump(self.reaction_roles, f, indent=4)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Evento cuando se agrega una reacción"""
        # Ignorar bots
        if payload.member and payload.member.bot:
            return
        
        await self.handle_reaction(payload, "add")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Evento cuando se remueve una reacción"""
        # Obtener el miembro ya que no viene en payload para remove
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if member and member.bot:
            return
        
        await self.handle_reaction(payload, "remove")
    
    async def handle_reaction(self, payload, action):
        """Maneja la lógica de agregar/remover roles"""
        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)
        
        print(f"🔍 Reacción {action}: {emoji} en mensaje {message_id}")
        
        # Verificar si esta mensaje tiene reaction roles configurados
        if (guild_id in self.reaction_roles and 
            message_id in self.reaction_roles[guild_id] and
            emoji in self.reaction_roles[guild_id][message_id]):
            
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = guild.get_member(payload.user_id)
            if not member:
                return
            
            role_data = self.reaction_roles[guild_id][message_id][emoji]
            role_id = role_data['role_id']
            role = guild.get_role(role_id)
            
            if not role:
                print(f"❌ Rol con ID {role_id} no encontrado")
                return
            
            try:
                if action == "add":
                    await member.add_roles(role)
                    print(f"✅ Rol {role.name} agregado a {member.display_name}")
                else:
                    await member.remove_roles(role)
                    print(f"❌ Rol {role.name} removido de {member.display_name}")
            except discord.Forbidden:
                print("❌ No tengo permisos para gestionar roles")
            except Exception as e:
                print(f"❌ Error gestionando rol: {e}")
        else:
            print(f"❌ No hay reaction role configurado para {emoji} en mensaje {message_id}")
    
    @commands.hybrid_command(name="reactionrole", description="Sistema de roles por reacción")
    @commands.has_permissions(administrator=True)
    async def reaction_role(self, ctx):
        """Comando principal para reaction roles"""
        embed = discord.Embed(
            title="🎭 Sistema de Reaction Roles",
            description="Configura roles que se asignan automáticamente al reaccionar a mensajes.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Comandos disponibles:",
            value=(
                "`/reactionrole add <message_id> <emoji> <role>` - Agregar reaction role\n"
                "`/reactionrole remove <message_id> <emoji>` - Remover reaction role\n"
                "`/reactionrole list` - Listar reaction roles activos\n"
                "`/reactionrole create` - Crear mensaje embed para reaction roles\n"
                "`/reactionrole create_channel <channel_id>` - Crear en canal específico"
            ),
            inline=False
        )
        await ctx.send(embed=embed)
    
    @reaction_role.error
    async def reaction_role_error(self, ctx, error):
        """Manejo de errores para el comando principal"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Necesitas permisos de administrador para usar este comando.", ephemeral=True)
    
    @commands.hybrid_command(name="reactionrole_add", description="Agregar un reaction role a un mensaje")
    @commands.has_permissions(administrator=True)
    async def add_reaction_role(self, ctx, message_id: str, emoji: str, role: discord.Role):
        """Agrega un reaction role a un mensaje existente"""
        try:
            # Convertir a string para el JSON
            guild_id = str(ctx.guild.id)
            message_id_str = str(message_id)
            
            # Buscar el mensaje en todos los canales del servidor
            message = None
            channel_found = None
            
            for channel in ctx.guild.text_channels:
                try:
                    message = await channel.fetch_message(int(message_id))
                    channel_found = channel
                    break
                except (discord.NotFound, discord.Forbidden):
                    continue
            
            if not message:
                await ctx.send("❌ No se encontró el mensaje con ese ID en ningún canal del servidor.", ephemeral=True)
                return
            
            # Verificar si el emoji es válido
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send("❌ Emoji inválido o no puedo reaccionar con él.", ephemeral=True)
                return
            
            # Inicializar estructura de datos si no existe
            if guild_id not in self.reaction_roles:
                self.reaction_roles[guild_id] = {}
            
            if message_id_str not in self.reaction_roles[guild_id]:
                self.reaction_roles[guild_id][message_id_str] = {}
            
            # AGREGAR EL REACTION ROLE A LA CONFIGURACIÓN
            self.reaction_roles[guild_id][message_id_str][emoji] = {
                'role_id': role.id,
                'role_name': role.name,
                'channel_id': channel_found.id
            }
            
            self.save_reaction_roles()
            
            embed = discord.Embed(
                title="✅ Reaction Role Agregado",
                color=discord.Color.green()
            )
            embed.add_field(name="📄 Mensaje ID", value=message_id, inline=True)
            embed.add_field(name="🎯 Emoji", value=emoji, inline=True)
            embed.add_field(name="🎭 Rol", value=role.mention, inline=True)
            embed.add_field(name="📺 Canal", value=channel_found.mention, inline=True)
            embed.add_field(name="🆔 ID del Rol", value=f"`{role.id}`", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}", ephemeral=True)
    
    @commands.hybrid_command(name="reactionrole_remove", description="Remover un reaction role de un mensaje")
    @commands.has_permissions(administrator=True)
    async def remove_reaction_role(self, ctx, message_id: str, emoji: str):
        """Remueve un reaction role de un mensaje"""
        guild_id = str(ctx.guild.id)
        message_id_str = str(message_id)
        
        if (guild_id in self.reaction_roles and 
            message_id_str in self.reaction_roles[guild_id] and
            emoji in self.reaction_roles[guild_id][message_id_str]):
            
            role_data = self.reaction_roles[guild_id][message_id_str].pop(emoji)
            
            # Limpiar estructura si está vacía
            if not self.reaction_roles[guild_id][message_id_str]:
                self.reaction_roles[guild_id].pop(message_id_str)
            if not self.reaction_roles[guild_id]:
                self.reaction_roles.pop(guild_id)
            
            self.save_reaction_roles()
            
            embed = discord.Embed(
                title="✅ Reaction Role Removido",
                color=discord.Color.orange()
            )
            embed.add_field(name="📄 Mensaje ID", value=message_id, inline=True)
            embed.add_field(name="🎯 Emoji", value=emoji, inline=True)
            embed.add_field(name="🎭 Rol", value=role_data['role_name'], inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No se encontró ese reaction role.", ephemeral=True)
    
    @commands.hybrid_command(name="reactionrole_list", description="Listar todos los reaction roles del servidor")
    @commands.has_permissions(administrator=True)
    async def list_reaction_roles(self, ctx):
        """Lista todos los reaction roles del servidor"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.reaction_roles or not self.reaction_roles[guild_id]:
            await ctx.send("📝 No hay reaction roles configurados en este servidor")
            return
        
        embed = discord.Embed(
            title="🎭 Reaction Roles Activos",
            color=discord.Color.blue()
        )
        
        for message_id, reactions in self.reaction_roles[guild_id].items():
            try:
                # Intentar obtener información del mensaje
                channel_id = list(reactions.values())[0]['channel_id']
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(int(message_id))
                        message_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content or "📝 Mensaje embed"
                    except discord.NotFound:
                        message_preview = "❌ Mensaje no encontrado"
                else:
                    message_preview = "❌ Canal no encontrado"
            except:
                message_preview = "❌ Error al cargar mensaje"
            
            reaction_list = []
            for emoji, data in reactions.items():
                role = ctx.guild.get_role(data['role_id'])
                role_mention = role.mention if role else f"❌ Rol no encontrado (ID: {data['role_id']})"
                reaction_list.append(f"{emoji} → {role_mention}")
            
            channel_mention = channel.mention if channel else "❌ Canal no encontrado"
            
            embed.add_field(
                name=f"📄 Mensaje ID: {message_id}",
                value=f"**Canal:** {channel_mention}\n**Contenido:** {message_preview}\n**Reacciones:**\n" + "\n".join(reaction_list),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="reactionrole_create", description="Crear un mensaje embed para reaction roles")
    @commands.has_permissions(administrator=True)
    async def create_reaction_role_message(self, ctx, titulo: str = "🎭 Reaction Roles", descripcion: str = "Reacciona para obtener roles"):
        """Crea un mensaje embed para reaction roles en el canal actual"""
        embed = discord.Embed(
            title=titulo,
            description=descripcion,
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📝 Cómo usar:",
            value=(
                "1. Reacciona al emoji correspondiente para obtener el rol\n"
                "2. Quita la reacción para remover el rol"
            ),
            inline=False
        )
        embed.set_footer(text="Configurado por: Infinity RB")
        
        message = await ctx.send(embed=embed)
        
        embed_info = discord.Embed(
            title="📋 Información para configurar",
            color=discord.Color.green()
        )
        embed_info.add_field(name="📄 Message ID", value=f"`{message.id}`", inline=True)
        embed_info.add_field(name="📺 Channel", value=ctx.channel.mention, inline=True)
        embed_info.add_field(
            name="🔧 Comando ejemplo", 
            value=f"`/reactionrole_add {message.id} ✅ @MiRol`",
            inline=False
        )
        
        await ctx.send(embed=embed_info, ephemeral=True)
    
    @commands.hybrid_command(name="reactionrole_create_channel", description="Crear mensaje de reaction roles en un canal específico")
    @commands.has_permissions(administrator=True)
    async def create_reaction_role_channel(self, ctx, channel_id: str, titulo: str = "🎭 Reaction Roles", descripcion: str = "Reacciona para obtener roles"):
        """Crea un mensaje embed para reaction roles en un canal específico usando su ID"""
        try:
            # Convertir el channel_id a entero
            channel_id_int = int(channel_id)
            
            # Buscar el canal en el servidor
            target_channel = ctx.guild.get_channel(channel_id_int)
            
            if not target_channel:
                await ctx.send("❌ No se encontró el canal con ese ID en este servidor.", ephemeral=True)
                return
            
            if not isinstance(target_channel, discord.TextChannel):
                await ctx.send("❌ El ID proporcionado no corresponde a un canal de texto.", ephemeral=True)
                return
            
            # Verificar permisos en el canal destino
            if not target_channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send(f"❌ No tengo permisos para enviar mensajes en {target_channel.mention}", ephemeral=True)
                return
            
            # Crear el embed de reaction roles
            embed = discord.Embed(
                title=titulo,
                description=descripcion,
                color=discord.Color.gold()
            )
            embed.add_field(
                name="📝 Cómo usar:",
                value=(
                    "1. Reacciona al emoji correspondiente para obtener el rol\n"
                    "2. Quita la reacción para remover el rol"
                ),
                inline=False
            )
            embed.set_footer(text="Configurado por: Infinity RB")
            
            # Enviar el mensaje al canal especificado
            message = await target_channel.send(embed=embed)
            
            # Enviar información de configuración al usuario
            embed_info = discord.Embed(
                title="✅ Mensaje de Reaction Roles Creado",
                color=discord.Color.green()
            )
            embed_info.add_field(name="📄 Message ID", value=f"`{message.id}`", inline=True)
            embed_info.add_field(name="📺 Canal Destino", value=target_channel.mention, inline=True)
            embed_info.add_field(
                name="🔧 Comando para agregar roles", 
                value=f"`/reactionrole_add {message.id} 🎯 @NombreDelRol`",
                inline=False
            )
            embed_info.add_field(
                name="📋 Emojis recomendados",
                value="✅ ❌ ⭐ 🎯 🎨 🔔 📢 🎭 🎮 📱 💻 🔒",
                inline=False
            )
            
            await ctx.send(embed=embed_info)
            
        except ValueError:
            await ctx.send("❌ ID de canal inválido. Debe ser un número.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para enviar mensajes en ese canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @commands.hybrid_command(name="reactionrole_clean", description="Limpiar reaction roles de mensajes eliminados")
    @commands.has_permissions(administrator=True)
    async def clean_reaction_roles(self, ctx):
        """Limpia los reaction roles de mensajes que ya no existen"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.reaction_roles or not self.reaction_roles[guild_id]:
            await ctx.send("📝 No hay reaction roles configurados en este servidor")
            return
        
        removed_count = 0
        messages_to_remove = []
        
        for message_id, reactions in self.reaction_roles[guild_id].items():
            try:
                # Buscar el canal del primer reaction role
                channel_id = list(reactions.values())[0]['channel_id']
                channel = ctx.guild.get_channel(channel_id)
                
                if channel:
                    # Intentar buscar el mensaje
                    await channel.fetch_message(int(message_id))
                else:
                    # Canal no encontrado, marcar para eliminar
                    messages_to_remove.append(message_id)
                    removed_count += 1
                    
            except discord.NotFound:
                # Mensaje no encontrado, marcar para eliminar
                messages_to_remove.append(message_id)
                removed_count += 1
            except Exception:
                # Otro error, mantener por seguridad
                continue
        
        # Eliminar los reaction roles de mensajes no encontrados
        for message_id in messages_to_remove:
            if message_id in self.reaction_roles[guild_id]:
                del self.reaction_roles[guild_id][message_id]
        
        # Eliminar el guild si está vacío
        if not self.reaction_roles[guild_id]:
            del self.reaction_roles[guild_id]
        
        self.save_reaction_roles()
        
        embed = discord.Embed(
            title="🧹 Limpieza Completada",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="📊 Resultados:",
            value=f"**Reaction roles eliminados:** {removed_count}\n**Reaction roles activos:** {len(self.reaction_roles.get(guild_id, {}))}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @add_reaction_role.error
    @remove_reaction_role.error
    @list_reaction_roles.error
    @create_reaction_role_message.error
    @create_reaction_role_channel.error
    @clean_reaction_roles.error
    async def reaction_role_commands_error(self, ctx, error):
        """Manejo de errores para comandos de reaction roles"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Necesitas permisos de administrador para usar este comando.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumentos inválidos. Verifica el ID del mensaje, emoji y rol.", ephemeral=True)
        else:
            await ctx.send(f"❌ Error: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReactionRole(bot))