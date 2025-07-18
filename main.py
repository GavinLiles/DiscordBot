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
    if issuper and message.attachments and message.channel.name == SUPERADMINCHAT:
        await SuperAdmin.process_tml(message, SUPERADMINCHAT, SUPERADMINROLE, MentorRole)
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


    






bot.run('') 
