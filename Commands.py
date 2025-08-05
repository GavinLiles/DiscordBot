#Holds all the discord bot commands
import discord

from discord.ext import commands
from dotenv import load_dotenv

#Creates a Voice channel
async def CreateTC(ctx, name):
    #do nothing if channel isn't admin
    if ctx.channel.name != "admin":
        return
    #set category to current category
    category = ctx.channel.category
    #check each channel if name exists and return if true
    if category and any(ch.name == name for ch in category.text_channels):
        await ctx.send(f"{name} already exists!")
        return
    #create channel
    await ctx.guild.create_text_channel(name, category=category)
    await ctx.send(f"{name} created")
#Deletes a text channel
async def DeleteTC(ctx, name):
    #do nothing and return if not in admin channel
    if ctx.channel.name != "admin":
        return
    #set category to current category
    category = ctx.channel.category
    #go through each text channel. If channel name matches name, delete channel and return
    for ch in category.text_channels:
        if ch.name == name:
            await ch.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")
#creates a voice channel
async def CreateVC(ctx, name):
    if ctx.channel.name != "admin":
        return

    category = ctx.channel.category
    if category and any(ch.name == name for ch in category.voice_channels):
        await ctx.send(f"{name} already exists!")
        return

    await ctx.guild.create_voice_channel(name, category=category)
    await ctx.send(f"{name} created")
#Deletes a voice channel
async def DeleteVC(ctx, name):
    if ctx.channel.name != "admin":
        return

    category = ctx.channel.category
    for ch in category.voice_channels:
        if ch.name == name:
            await ch.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")
#This will turn links on or off
async def links(ctx, link_control, setting: str):
    if ctx.channel.name != "admin":
        return

    link_control[ctx.guild.id] = setting.lower() == "on"
    await ctx.send(f"Links have been turned {'on' if setting.lower() == 'on' else 'off'}.")
#This will delete a certain amount or all messages in a channel
async def Clear(ctx, amount : str):
    if amount.lower() == "all":
        await ctx.channel.purge()
        return

    if not amount.isdigit():
        await ctx.send("Please enter a whole number e.g (!clear 100) or use 'all.'")
        return

    count = int(amount)
    if count == 0:
        await ctx.send("Please enter a number greater than 0.")
    else:
        await ctx.channel.purge(limit=count + 1)

#deletes a category, including the channels and roles connected to said category
async def DeleteCategory(ctx, message, bot, MENTORROLE):
    if str(ctx.channel) == 'superadminchat':

        for category in ctx.guild.categories:
            if message == str(category):
                await ctx.send("Are you sure you want to delete this category? (yes/no)")
                confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
                if confirm.content.lower() == "yes":
                    for ch in category.channels:
                        await ch.delete()
                    
                    await category.delete()
                    try:
                        await discord.utils.get(message.guild.roles, name=f"{message} {MENTORROLE}").delete()
                        await discord.utils.get(message.guild.roles, name=message).delete()
                    except:
                        return
                    return
        await ctx.send("Category not real!")
        
#revokes a specific role from everyone
async def RevokeRoles(ctx, message, bot):
    if str(ctx.channel) == 'superadminchat':
        try:
            role = discord.utils.get(ctx.guild.roles, name=message)

            await ctx.channel.send("Are you sure you want to remove the role? (yes/no)")
            confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            if confirm.content.lower() == "yes":
                for member in ctx.guild.members:
                    if role in member.roles:
                        await member.remove_roles(role)
        except:
            print(f"role {message} not found")