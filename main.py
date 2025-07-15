import discord
import tomllib  # Available in Python 3.11+

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
                toml_text = toml_bytes.decode("utf-8") 

                print(f"📥 Received file: {attachment.filename}")
                print(f"Type: {type(toml_bytes)} | First 100 bytes: {toml_bytes[:100]!r}")

                try:
                    data = tomllib.loads(toml_text)
                    num_classes = len(data.get('classes', []))
                    class_names = [cls["name"] for cls in data["classes"]]
                    await message.channel.send(
                        f"Parsed TOML with {num_classes} classes:\n{', '.join(class_names)}"
                    )
                except Exception as e:
                    await message.channel.send(f"Error parsing TOML: {e}")

client.run('') 
