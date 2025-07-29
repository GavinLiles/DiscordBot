import discord
from discord.ext import commands
import tomllib
import SuperAdmin
import Control
import logging
from dotenv import load_dotenv

from dotenv import load_dotenv
import os
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
# Environment variables 

SUPERADMINCHAT=os.getenv('SUPERADMINCHAT', 'SUPERADMINCHAT')
SUPERADMINROLE=os.getenv('SUPERADMINROLE', 'SuperAdmin')
MentorRole=os.getenv('MentorRole', 'Mentor')
#discord intents
#Basically what the bot is allowed to do in the server
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True
handler = logging.FileHandler(filename='discord.log', encoding ='utf-8', mode='w')
#client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents = intents)

# Event handlers
@bot.event
#On ready is called on bootup
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
#On message is called everytime a message is sent in a discord with this bot
async def on_message(message):
    #ignore messages sent by the bot itself
    if message.author == bot.user:
        return
    
    #Check if the message is sent by a super admin should be moved lower when we have more built up for efficeny
    #We use any()) because the roles a user has is a list so you cant just  do message.author.role == SUPERADMINROLE
    #Have to check if any is faster then a for loop or another loop structure
    issuper = any(role.name == SUPERADMINROLE for role in message.author.roles)

    #Check if the message is in the super admin chat and is an attachment
    #Again we will move this to the bottom when more is added because realisitcly this command will only happen once a semester
    if message.channel.name == SUPERADMINCHAT and issuper:
        if message.attachments:
            await SuperAdmin.process_tml(message, SUPERADMINCHAT, SUPERADMINROLE, MentorRole)
        elif message.content.startswith('delete'):
            category = message.content.split(' ', 1)[1]
            existing = discord.utils.get(message.guild.categories, name=category)
            await message.channel.send("Are you sure you want to remove this category? (yes/no)")
            if (await bot.wait_for('message', check=lambda m: m.author == message.author and m.channel == message.channel)).content == 'yes':
                if existing:
                    for channel in existing.channels:
                        await channel.delete()
                    await discord.utils.get(message.guild.roles, name=category + " " + MentorRole).delete()
                    await discord.utils.get(message.guild.roles, name=category).delete()
                    await existing.delete()
        elif message.content.startswith('remove'):
            category = message.content.split(' ', 1)[1]
            role = discord.utils.get(message.guild.roles, name=category)
            await message.channel.send("Are you sure you want to remove the role? (yes/no)")
            if (await bot.wait_for('message', check=lambda m: m.author == message.author and m.channel == message.channel)).content == 'yes':
                for member in message.guild.members:
                    if role in member.roles:
                        await member.remove_roles(role)

     #checking link setting
    link_allowed = link_control.get(message.guild.id, True) #default is true, allowing links
    if not link_allowed and ('https://'in message.content or 'http://' in message.content): 
        await message.delete()
        await message.channel.send(f"{message.author.mention} links are currently disabled.")

    await bot.process_commands(message)


@bot.command()
async def Create(ctx,*, message):
    category = ctx.channel.category
    if ctx.channel.name != 'admin':
      await  ctx.send("Wrong channel")
      return
    if category:
        for channel in category.text_channels:
            if(message == str(channel)):
                await ctx.send(f"{message} already exists!")
                return
    await ctx.guild.create_text_channel(message, category = ctx.channel.category)
    await ctx.send(f"{message} created")

@bot.command()
async def Delete(ctx,*,message):
    category = ctx.channel.category
    if ctx.channel.name != 'admin':
        await ctx.send("Wrong channel")
        return
    for channel in category.text_channels:
        if(message == str(channel)):
            await channel.delete()
            ctx.send(f"{message} has been deleted")
            return
    await ctx.send("Channel does not exist")

link_control = {}

@bot.command()
async def links(ctx, setting: str):
    if ctx.channel.name != 'admin':
        await ctx.send("Wrong channel")
        return
    elif setting.lower() == 'off':
        link_control[ctx.guild.id] = False
    elif setting.lower() == 'on':
        link_control[ctx.guild.id] = True

# admin must be in the chat to clear messages
@bot.command()
async def Clear(ctx, amount:str): # clears a number of messages
    if amount.lower() == 'all':
        await ctx.channel.purge()
        return
    else:
        if not amount.isdigit():
            await ctx.send("Please enter a whole number e.g (!clear 100) or use 'all.'")
            return
        amount = int(amount)
        if amount == 0:
            await ctx.send("Please enter number that is greater than 0.")
            return
        else:
            await ctx.channel.purge(limit = amount + 1) # +1 to include the bot command





bot.run(token) 
