import discord
from slack import update_channel_map
import tomllib
import tomli_w
import secrets
import asyncio
import os
TOKENS = os.getenv("TOKENS", "group_tokens.toml")

async def create_group_structure(guild, cls, MentorRole, message, group_dump):
    # Create roles
    mentor = await guild.create_role(
        name=cls["name"] + " " + MentorRole,
        mentionable=True,
        color=discord.Color.orange()
    )
    user = await guild.create_role(
        name=cls["name"],
        mentionable=True,
        color=discord.Color.green()
    )

    # Create category
    category = await guild.create_category(cls["name"])
    await category.set_permissions(mentor, read_messages=True, send_messages=True, connect=True, speak=True)
    await category.set_permissions(user, read_messages=True, send_messages=True, connect=True, speak=True)
    await category.set_permissions(guild.default_role, read_messages=False, connect=False)

    # Create default text channels
    HardChannels = ["General", "Sources", "GitHub", "Offtopic"]
    for name in HardChannels:
        ch = await guild.create_text_channel(name, category=category)
        if name == "General":
            slack_id = cls.get("slack", "").strip()
            if slack_id:
                update_channel_map(slack_id, str(ch.id))

    # Create Admin with limited access
    admin = await guild.create_text_channel("Admin", category=category)
    await admin.set_permissions(mentor, read_messages=True, send_messages=True, connect=True, speak=True)
    await admin.set_permissions(user, read_messages=False, send_messages=False, connect=False, speak=False)

    # Default voice channels
    await guild.create_voice_channel("General_1", category=category)
    await guild.create_voice_channel("General_2", category=category)

    # Add extras from TOML
    extra_text = [ch.strip() for ch in cls.get("text_channels", "").split(",") if ch.strip()]
    for ch in extra_text:
        if ch not in HardChannels:
            await guild.create_text_channel(ch, category=category)

    extra_voice = [ch.strip() for ch in cls.get("voice_channels", "").split(",") if ch.strip()]
    for ch in extra_voice:
        if ch not in ["General_1", "General_2"]:
            await guild.create_voice_channel(ch, category=category)

    # initialize group token storage
    group_name = cls["name"]
    group_dump[group_name] = {"tokens": []}

    # generate student tokens
    for i in range(int(cls["students"])):
        group_dump[group_name]["tokens"].append({
            "token": secrets.token_hex(32),
            "index": i,
            "role": "student",
            "used": False
        })

    # generate mentor tokens
    for i in range(int(cls["mentor"])):
        group_dump[group_name]["tokens"].append({
            "token": secrets.token_hex(32),
            "index": i,
            "role": "mentor",
            "used": False
        })

    return category

def delete_group_tokens(group_name: str) -> None:
    if not os.path.exists(TOKENS):
        return

    try:
        with open(TOKENS, "rb") as infile:
            tokens_data = tomllib.load(infile)

        if group_name in tokens_data:
            del tokens_data[group_name]

            with open(TOKENS, "wb") as infile:
                infile.write(tomli_w.dumps(tokens_data).encode("utf-8"))
    except:
        pass  


async def process_tml(message: discord.Message, SUPERADMINCHAT: str, SUPERADMINROLE: str, MentorRole: str):
    #Loops through all attachments in a message
    for attachment in message.attachments:

        #Extract and read file if it's a toml file
        if attachment.filename.endswith('.toml'):

            #This takes the toml file and reads it in as binary data then decodes it to a string
            toml_text = (await attachment.read()).decode("utf-8")

            #Open toml file and extract data
            try:
                #parse the toml file and load it into a python dictionary
                data = tomllib.loads(toml_text)

                # create a global token dump for all groups
                group_dump = {}

                #Create a catagory for each group in the dict
                for cls in data["groups"]:
                    #check if the group name is already in use
                    existing = discord.utils.get(message.guild.categories, name=cls["name"])

                    #creates group roles and categories
                    if not existing:
                        await create_group_structure(message.guild, cls, MentorRole, message, group_dump)
                    else:
                        #if it exists give them a menu with option to select
                        await message.channel.send(
                            f"The `{cls['name']}` category already exists!\n"
                            f"Please choose how to proceed:\n"
                            f"`skip` — Leave the existing group as-is.\n"
                            f"`replace` — Delete the existing group and recreate it.\n"
                            f"`merge` — Add any missing channels.\n\n"
                            f"Defaulting to `skip` after 60 seconds."
                        )
                        try:
                            reply = await message.client.wait_for("message", timeout=60.0, check=lambda m: m.author == message.author and m.channel == message.channel and m.content.lower() in ["skip", "replace", "merge"])
                            user_choice = reply.content.lower()
                            await message.channel.send(f"You selected `{user_choice}`.")
                        except asyncio.TimeoutError:
                            user_choice = "skip"
                            await message.channel.send("Time expired. Defaulting to `skip`.")
                        if user_choice == "merge":
                            existing_channel_names = [ch.name for ch in existing.channels]
                            extra_text_channels = [ch.strip() for ch in cls.get("text_channels", "").split(",") if ch.strip()]
                            for extra in extra_text_channels:
                                if extra not in existing_channel_names:
                                    await message.guild.create_text_channel(extra, category=existing)

                            extra_voice_channels = [ch.strip() for ch in cls.get("voice_channels", "").split(",") if ch.strip()]
                            for extra in extra_voice_channels:
                                if extra not in existing_channel_names:
                                    await message.guild.create_voice_channel(extra, category=existing)
                        elif user_choice == "replace":
                            category = discord.utils.get(message.guild.categories, name=cls["name"])
                            if category:
                                for ch in category.channels:
                                    await ch.delete()
                                await category.delete()

                            # Delete associated roles if they exist
                            mentor_role = discord.utils.get(message.guild.roles, name=f"{cls["name"]} {MentorRole}")
                            user_role = discord.utils.get(message.guild.roles, name=cls["name"])

                            if mentor_role:
                                await mentor_role.delete()
                            if user_role:
                                await user_role.delete()
                            await create_group_structure(message.guild, cls, MentorRole, message, group_dump)




                            

                # Write all tokens for all groups to file
                with open(TOKENS, "wb") as f:
                    tomli_w.dump(group_dump, f)

            #print error message if error      
            except Exception as e:
                await message.channel.send(f"Error parsing TOML: {e}")

