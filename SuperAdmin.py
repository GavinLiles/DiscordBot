import discord
from slack import update_channel_map
import tomllib
import tomli_w
import secrets
import asyncio
import os
import Commands
from locking import group_tokens_lock

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

    # Create category and set perms
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

    # Create Admin for mentors only
    admin = await guild.create_text_channel("Admin", category=category)
    await admin.set_permissions(mentor, read_messages=True, send_messages=True, connect=True, speak=True)
    await admin.set_permissions(user, read_messages=False, send_messages=False, connect=False, speak=False)

    # Create default voice channels
    await guild.create_voice_channel("General_1", category=category)
    await guild.create_voice_channel("General_2", category=category)

    # Add extra channels from TOML
    extra_text = [ch.strip() for ch in cls.get("text_channels", "").split(",") if ch.strip()]
    for ch in extra_text:
        if ch not in HardChannels:
            await guild.create_text_channel(ch, category=category)

    extra_voice = [ch.strip() for ch in cls.get("voice_channels", "").split(",") if ch.strip()]
    for ch in extra_voice:
        if ch not in ["General_1", "General_2"]:
            await guild.create_voice_channel(ch, category=category)
    # Add the tokens for students and mentors
    group_name = cls["name"]
    total_students = int(cls.get("students", 0))
    total_mentors = int(cls.get("mentor", 0))

    await append_or_create_group(group_name, num_students=total_students, num_mentors=total_mentors)

    return category

#delete all tokens from a group
async def delete_group_tokens(group_name: str) -> None:
    print(f"Deleting group: '{group_name}' from token file: {TOKENS}")

    if not os.path.exists(TOKENS):
        print("Token file does not exist.")
        return

    try:
        #check if anything is using it
        async with group_tokens_lock:
            #load in the tokens
            with open(TOKENS, "rb") as infile:
                tokens_data = tomllib.load(infile)
                print(f"Groups currently in file: {list(tokens_data.keys())}")
            # look for the group that is in question and the delete it
            # finally rewrite it to the file
            if group_name in tokens_data:
                del tokens_data[group_name]
                print(f"Group '{group_name}' removed from in-memory data.")

                with open(TOKENS, "wb") as outfile:
                    outfile.write(tomli_w.dumps(tokens_data).encode("utf-8"))
                print("Token file updated successfully.")

                with open(TOKENS, "rb") as verify:
                    check_data = tomllib.load(verify)
                    if group_name not in check_data:
                        print(f"Group '{group_name}' deletion confirmed.")
                    else:
                        print(f"Warning: Group '{group_name}' still exists after attempted deletion.")
            else:
                print(f"Group '{group_name}' not found in token file.")
    except Exception as e:
        print(f"Error while deleting group tokens: {e}")

# this function creates or updates a groups tokens in the file
async def append_or_create_group(group_name: str, num_students: int = 0, num_mentors: int = 0, tokens_file: str = TOKENS) -> None:
    async with group_tokens_lock:
        if os.path.exists(tokens_file):
            with open(tokens_file, "rb") as f:
                token_data = tomllib.load(f)
        else:
            token_data = {}
        #if the group does not exist make it
        if group_name not in token_data:
            token_data[group_name] = {
                "tokens": [],
                "used": [],
                "roles": []
            }
        # Generate student tokens
        for _ in range(num_students):
            token_data[group_name]["tokens"].append(secrets.token_hex(32))
            token_data[group_name]["used"].append(False)
            token_data[group_name]["roles"].append("student")
        # generate mentor tokens
        for _ in range(num_mentors):
            token_data[group_name]["tokens"].append(secrets.token_hex(32))
            token_data[group_name]["used"].append(False)
            token_data[group_name]["roles"].append("mentor")
        #write to file
        with open(tokens_file, "wb") as f:
            f.write(tomli_w.dumps(token_data).encode("utf-8"))

    print(f"Group '{group_name}' updated. +{num_students} student(s), +{num_mentors} mentor(s)")

#this function will take a toml sent to a channel to create replace or merge a group
async def process_tml(bot: discord.Client, message: discord.Message, SUPERADMINCHAT: str, SUPERADMINROLE: str, MentorRole: str):
    for attachment in message.attachments:
        if attachment.filename.endswith('.toml'):
            toml_text = (await attachment.read()).decode("utf-8")

            try:
                #put the toml into a dict
                data = tomllib.loads(toml_text)
                group_dump = {}

                # for every element in the toml check if the category exists or not
                for cls in data["groups"]:
                    existing = discord.utils.get(message.guild.categories, name=cls["name"])
                    #if it does not exist go to reate_group_structure to make the new group
                    if not existing:
                        await create_group_structure(message.guild, cls, MentorRole, message, group_dump)
                    #if it does not exist give the user options to merge it replace it and or skip it in the file
                    else:
                        await message.channel.send(
                            f"The `{cls['name']}` category already exists!\n"
                            f"Please choose how to proceed:\n"
                            f"`skip` — Leave the existing group as-is.\n"
                            f"`replace` — Delete the existing group and recreate it.\n"
                            f"`merge` — Add any missing channels.\n\n"
                            f"Defaulting to `skip` after 60 seconds."
                        )
                        #if no user input skip after 60 seconds
                        try:
                            reply = await bot.wait_for(
                                "message",
                                timeout=60.0,
                                check=lambda m: m.author == message.author and m.channel == message.channel and m.content.lower() in ["skip", "replace", "merge"]
                            )

                            user_choice = reply.content.lower()
                            await message.channel.send(f"You selected `{user_choice}`.")
                        except asyncio.TimeoutError:
                            user_choice = "skip"
                            await message.channel.send("Time expired. Defaulting to `skip`.")
                        # if they select merge add new channels that did not already exist and add more tokens
                        # to make up the difrence in the new student count vs the old
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

                            group_name = cls["name"]
                            total_students = int(cls.get("students", 0))
                            total_mentors = int(cls.get("mentor", 0))

                            if os.path.exists(TOKENS):
                                with open(TOKENS, "rb") as f:
                                    token_data = tomllib.load(f)
                            else:
                                token_data = {}

                            existing = token_data.get(group_name, {"roles": []})
                            current_students = existing["roles"].count("student")
                            current_mentors = existing["roles"].count("mentor")

                            add_students = max(0, total_students - current_students)
                            add_mentors = max(0, total_mentors - current_mentors)

                            await append_or_create_group(group_name, num_students=add_students, num_mentors=add_mentors)
                        #if they replace just remove all the old and remake it
                        elif user_choice == "replace":
                            await Commands.delete_group_category(message.guild, cls["name"], MentorRole)


                            await create_group_structure(message.guild, cls, MentorRole, message, group_dump)

            except Exception as e:
                await message.channel.send(f"Error parsing TOML: {e}")