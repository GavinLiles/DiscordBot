import discord
import tomllib

from dotenv import load_dotenv
import os

# Environment variables 
load_dotenv()
SUPERADMINCHAT=os.getenv('SUPERADMINCHAT', 'SUPERADMINCHAT')
SUPERADMINROLE=os.getenv('SUPERADMINROLE', 'SuperAdmin')

#discord intents
#Basically what the bot is allowed to do in the server
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
client = discord.Client(intents=intents)

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

        #This is used to loop through all attachments in a given message
        for attachment in message.attachments:

            #if the attachment is a toml file we should start reading it and extracting info to build out our new section of the discord
            if attachment.filename.endswith('.toml'):


                #This takes the toml file and reads it in as binary data then decodes it to a string
                toml_text = (await attachment.read()).decode("utf-8")

                #print the file its reading to the console for error checking can be removed later
                print(f"Received file: {attachment.filename}")


                #We should use trys and excepts for almost everythin we do with this bot to determin errors quickly
                #This try block will attempt to parse the toml file and extract the classes and their names
                #If it fails it will print the error to the discord channel
                try:
                    #parse the toml file and load it into a python dictionary
                    data = tomllib.loads(toml_text)
                    #Create a catagory for each class in the dict
                    for cls in data["classes"]:
                        #check if the class name is already in use
                        existing = discord.utils.get(message.guild.categories, name=cls["name"])
                        #if it is we should not create a new category
                        #We should discuss what we are going to do in this situation further but for now it will just skip it
                        if not existing:
                            #Create a new category for the class
                            NewCategory = await message.guild.create_category(cls["name"])
                            HardChannels = ["Admin","General", "Sources", "GitHub", "Offtopic"]
                            for HardChannel in HardChannels:
                                #Create a new text channel for the class
                                await message.guild.create_text_channel(HardChannel, category=NewCategory)
                            await message.guild.create_voice_channel("General", category=NewCategory)
                            
                except Exception as e:
                    await message.channel.send(f"Error parsing TOML: {e}")

client.run('') 
