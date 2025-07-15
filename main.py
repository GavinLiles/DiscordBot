# This example requires the 'message_content' intent.

import discord
import tomllib



intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith('.toml'):
                toml_bytes = await attachment.read()
                toml_bytes = await attachment.read()  # bytes from Discord attachment
                try:
                    data = tomllib.loads(toml_bytes)  # pass bytes directly
                except Exception as e:
                    await message.channel.send(f"Error parsing TOML: {e}")




client.run('')
