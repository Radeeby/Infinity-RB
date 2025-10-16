import discord
from discord.ext import commands
from discord import app_commands

class BotSay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="say", description="Envía un mensaje como el bot en un canal específico")
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, channel_id: str, *, mensaje: str):
        """Envía un mensaje como el bot en un canal específico"""
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
            
            # Enviar el mensaje al canal especificado
            await target_channel.send(mensaje)
            
            # Confirmación al usuario
            embed = discord.Embed(
                title="✅ Mensaje Enviado",
                color=discord.Color.green()
            )
            embed.add_field(name="📺 Canal", value=target_channel.mention, inline=True)
            embed.add_field(name="📝 Mensaje", value=f"```{mensaje}```", inline=False)
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await ctx.send("❌ ID de canal inválido. Debe ser un número.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para enviar mensajes en ese canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="say_embed", description="Envía un mensaje embed como el bot en un canal específico")
    @commands.has_permissions(administrator=True)
    async def say_embed(self, ctx, channel_id: str, titulo: str, *, descripcion: str = ""):
        """Envía un mensaje embed como el bot en un canal específico"""
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
            
            # Crear el embed
            embed = discord.Embed(
                title=titulo,
                description=descripcion,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Enviado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            
            # Enviar el embed al canal especificado
            await target_channel.send(embed=embed)
            
            # Confirmación al usuario
            confirm_embed = discord.Embed(
                title="✅ Embed Enviado",
                color=discord.Color.green()
            )
            confirm_embed.add_field(name="📺 Canal", value=target_channel.mention, inline=True)
            confirm_embed.add_field(name="🎯 Título", value=titulo, inline=True)
            confirm_embed.add_field(name="📝 Descripción", value=descripcion[:100] + "..." if len(descripcion) > 100 else descripcion, inline=False)
            
            await ctx.send(embed=confirm_embed, ephemeral=True)
            
        except ValueError:
            await ctx.send("❌ ID de canal inválido. Debe ser un número.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para enviar mensajes en ese canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="say_advanced", description="Envía un mensaje embed avanzado con color personalizado")
    @commands.has_permissions(administrator=True)
    async def say_advanced(self, ctx, channel_id: str, titulo: str, color: str = "blue", *, descripcion: str = ""):
        """Envía un mensaje embed avanzado con color personalizado"""
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
            
            # Mapeo de colores
            color_map = {
                "blue": discord.Color.blue(),
                "red": discord.Color.red(),
                "green": discord.Color.green(),
                "yellow": discord.Color.yellow(),
                "purple": discord.Color.purple(),
                "orange": discord.Color.orange(),
                "pink": discord.Color.pink(),
                "gold": discord.Color.gold(),
                "teal": discord.Color.teal(),
                "dark_blue": discord.Color.dark_blue(),
                "dark_green": discord.Color.dark_green(),
                "dark_red": discord.Color.dark_red(),
                "dark_purple": discord.Color.dark_purple(),
                "dark_gold": discord.Color.dark_gold(),
                "dark_teal": discord.Color.dark_teal(),
            }
            
            # Obtener el color
            embed_color = color_map.get(color.lower(), discord.Color.blue())
            
            # Crear el embed
            embed = discord.Embed(
                title=titulo,
                description=descripcion,
                color=embed_color
            )
            embed.set_footer(text=f"Enviado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            
            # Enviar el embed al canal especificado
            await target_channel.send(embed=embed)
            
            # Confirmación al usuario
            confirm_embed = discord.Embed(
                title="✅ Embed Avanzado Enviado",
                color=discord.Color.green()
            )
            confirm_embed.add_field(name="📺 Canal", value=target_channel.mention, inline=True)
            confirm_embed.add_field(name="🎯 Título", value=titulo, inline=True)
            confirm_embed.add_field(name="🎨 Color", value=color, inline=True)
            confirm_embed.add_field(name="📝 Descripción", value=descripcion[:100] + "..." if len(descripcion) > 100 else descripcion, inline=False)
            
            await ctx.send(embed=confirm_embed, ephemeral=True)
            
        except ValueError:
            await ctx.send("❌ ID de canal inválido. Debe ser un número.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para enviar mensajes en ese canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="say_reply", description="Envía un mensaje como respuesta a otro mensaje")
    @commands.has_permissions(administrator=True)
    async def say_reply(self, ctx, channel_id: str, message_id: str, *, mensaje: str):
        """Envía un mensaje como respuesta a otro mensaje específico"""
        try:
            # Convertir los IDs a enteros
            channel_id_int = int(channel_id)
            message_id_int = int(message_id)
            
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
            
            # Buscar el mensaje al que responder
            try:
                target_message = await target_channel.fetch_message(message_id_int)
            except discord.NotFound:
                await ctx.send("❌ No se encontró el mensaje con ese ID en el canal especificado.", ephemeral=True)
                return
            
            # Enviar el mensaje como respuesta
            await target_message.reply(mensaje)
            
            # Confirmación al usuario
            embed = discord.Embed(
                title="✅ Mensaje de Respuesta Enviado",
                color=discord.Color.green()
            )
            embed.add_field(name="📺 Canal", value=target_channel.mention, inline=True)
            embed.add_field(name="📄 Mensaje Respondido", value=f"ID: `{message_id}`", inline=True)
            embed.add_field(name="📝 Mensaje", value=f"```{mensaje}```", inline=False)
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await ctx.send("❌ ID de canal o mensaje inválido. Deben ser números.", ephemeral=True)
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para enviar mensajes en ese canal.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", ephemeral=True)

    @commands.hybrid_command(name="say_help", description="Muestra ayuda para los comandos de say")
    @commands.has_permissions(administrator=True)
    async def say_help(self, ctx):
        """Muestra ayuda para todos los comandos de say"""
        embed = discord.Embed(
            title="🤖 Comandos Say - Ayuda",
            description="Comandos para enviar mensajes como el bot",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 `/say <channel_id> <mensaje>`",
            value="Envía un mensaje de texto normal al canal especificado",
            inline=False
        )
        
        embed.add_field(
            name="🎨 `/say_embed <channel_id> <titulo> [descripcion]`",
            value="Envía un mensaje embed básico al canal especificado",
            inline=False
        )
        
        embed.add_field(
            name="🚀 `/say_advanced <channel_id> <titulo> <color> [descripcion]`",
            value="Envía un mensaje embed con color personalizado\n**Colores disponibles:** blue, red, green, yellow, purple, orange, pink, gold, teal, dark_blue, dark_green, dark_red, dark_purple, dark_gold, dark_teal",
            inline=False
        )
        
        embed.add_field(
            name="↩️ `/say_reply <channel_id> <message_id> <mensaje>`",
            value="Envía un mensaje como respuesta a otro mensaje específico",
            inline=False
        )
        
        embed.add_field(
            name="💡 Cómo obtener IDs:",
            value="• **ID de Canal:** Click derecho en el canal → Copiar ID\n• **ID de Mensaje:** Click derecho en el mensaje → Copiar ID\n*(Debes tener activado el Modo Desarrollador en Discord)*",
            inline=False
        )
        
        embed.set_footer(text="Todos los comandos requieren permisos de administrador")
        
        await ctx.send(embed=embed, ephemeral=True)

    @say.error
    @say_embed.error
    @say_advanced.error
    @say_reply.error
    async def say_commands_error(self, ctx, error):
        """Manejo de errores para los comandos say"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Necesitas permisos de administrador para usar este comando.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumentos inválidos. Revisa la sintaxis del comando.", ephemeral=True)
        else:
            await ctx.send(f"❌ Error: {str(error)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BotSay(bot))