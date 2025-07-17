import discord
import tomllib
import SuperAdmin
import Control

from dotenv import load_dotenv
import os

# Environment variables 
load_dotenv()
SUPERADMINCHAT=os.getenv('SUPERADMINCHAT', 'SUPERADMINCHAT')
SUPERADMINROLE=os.getenv('SUPERADMINROLE', 'SuperAdmin')
MentorRole=os.getenv('MentorRole', 'Mentor')
#discord intents
#Basically what the bot is allowed to do in the server
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
client = discord.Client(command_prefix = '!', intents=intents)

# Event handlers
@client.event
#On ready is called on bootup
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
#On message is called everytime a message is sent in a discord with this bot
async def on_message(message):
    #ignore messages sent by the bot itself
    if message.author == client.user:
        return
    
    #Check if the message is sent by a super admin should be moved lower when we have more built up for efficeny
    #We use any()) because the roles a user has is a list so you cant just  do message.author.role == SUPERADMINROLE
    #Have to check if any is faster then a for loop or another loop structure
    issuper = any(role.name == SUPERADMINROLE for role in message.author.roles)


    #Check if the message is in the super admin chat and is an attachment
    #Again we will move this to the bottom when more is added because realisitcly this command will only happen once a semester
    if issuper and message.attachments and message.channel.name == SUPERADMINCHAT:
        await SuperAdmin.process_tml(message, SUPERADMINCHAT, SUPERADMINROLE, MentorRole)
    await message.channel.send(f"This is a test")
client.run('') 
