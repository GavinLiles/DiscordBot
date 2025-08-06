import discord
from slack import update_channel_map
import tomllib
import tomli_w
import secrets
import asyncio
import os
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

    group_name = cls["name"]
    total_students = int(cls.get("students", 0))
    total_mentors = int(cls.get("mentor", 0))

    await append_or_create_group(group_name, num_students=total_students, num_mentors=total_mentors)

    return category

async def delete_group_tokens(group_name: str) -> None:
    print(f"Deleting group: '{group_name}' from token file: {TOKENS}")

    if not os.path.exists(TOKENS):
        print("Token file does not exist.")
        return

    try:
        async with group_tokens_lock:
            with open(TOKENS, "rb") as infile:
                tokens_data = tomllib.load(infile)
                print(f"Groups currently in file: {list(tokens_data.keys())}")

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


async def append_or_create_group(group_name: str, num_students: int = 0, num_mentors: int = 0, tokens_file: str = TOKENS) -> None:
    async with group_tokens_lock:
        if os.path.exists(tokens_file):
            with open(tokens_file, "rb") as f:
                token_data = tomllib.load(f)
        else:
            token_data = {}

        if group_name not in token_data:
            token_data[group_name] = {
                "tokens": [],
                "used": [],
                "roles": []
            }

        for _ in range(num_students):
            token_data[group_name]["tokens"].append(secrets.token_hex(32))
            token_data[group_name]["used"].append(False)
            token_data[group_name]["roles"].append("student")

        for _ in range(num_mentors):
            token_data[group_name]["tokens"].append(secrets.token_hex(32))
            token_data[group_name]["used"].append(False)
            token_data[group_name]["roles"].append("mentor")

        with open(tokens_file, "wb") as f:
            f.write(tomli_w.dumps(token_data).encode("utf-8"))

    print(f"Group '{group_name}' updated. +{num_students} student(s), +{num_mentors} mentor(s)")


async def process_tml(bot: discord.Client, message: discord.Message, SUPERADMINCHAT: str, SUPERADMINROLE: str, MentorRole: str):
    for attachment in message.attachments:
        if attachment.filename.endswith('.toml'):
            toml_text = (await attachment.read()).decode("utf-8")

            try:
                data = tomllib.loads(toml_text)
                group_dump = {}

                for cls in data["groups"]:
                    existing = discord.utils.get(message.guild.categories, name=cls["name"])

                    if not existing:
                        await create_group_structure(message.guild, cls, MentorRole, message, group_dump)
                    else:
                        await message.channel.send(
                            f"The `{cls['name']}` category already exists!\n"
                            f"Please choose how to proceed:\n"
                            f"`skip` — Leave the existing group as-is.\n"
                            f"`replace` — Delete the existing group and recreate it.\n"
                            f"`merge` — Add any missing channels.\n\n"
                            f"Defaulting to `skip` after 60 seconds."
                        )
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

                        elif user_choice == "replace":
                            category = discord.utils.get(message.guild.categories, name=cls["name"])
                            if category:
                                for ch in category.channels:
                                    await ch.delete()
                                await category.delete()

                            mentor_role = discord.utils.get(message.guild.roles, name=f"{cls['name']} {MentorRole}")
                            user_role = discord.utils.get(message.guild.roles, name=cls["name"])

                            if mentor_role:
                                await mentor_role.delete()
                            if user_role:
                                await user_role.delete()

                            await create_group_structure(message.guild, cls, MentorRole, message, group_dump)

            except Exception as e:
                await message.channel.send(f"Error parsing TOML: {e}")