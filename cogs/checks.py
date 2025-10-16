import discord
from discord.ext import commands
import config

def has_normal_role():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        normal_role = ctx.guild.get_role(config.ROLES["NORMAL"])
        if normal_role and normal_role in ctx.author.roles:
            return True
        await ctx.send("❌ No tienes el rol necesario para usar este comando.", ephemeral=True)
        return False
    return commands.check(predicate)

def has_admin_role():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        admin_role = ctx.guild.get_role(config.ROLES["ADMIN"])
        if admin_role and admin_role in ctx.author.roles:
            return True
        await ctx.send("❌ No tienes permisos de administrador para usar este comando.", ephemeral=True)
        return False
    return commands.check(predicate)