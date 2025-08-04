import discord
from discord.ext import commands
import tomllib
import SuperAdmin
import Control
import logging
import asyncio
import os
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SUPERADMINCHAT = os.getenv("SUPERADMINCHAT", "SUPERADMINCHAT")
SUPERADMINROLE = os.getenv("SUPERADMINROLE", "SuperAdmin")
MentorRole = os.getenv("MentorRole", "Mentor")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
bot = commands.Bot(command_prefix="!", intents=intents)
link_control = {}

# Load channel map
try:
    with open("channel_map.toml", "rb") as f:
        config = tomllib.load(f)
except Exception as e:
    print(e)

CHANNEL_MAP = {}
for slack_id, discord_id in config.get("channels", {}).items():
    CHANNEL_MAP[slack_id] = discord_id
    CHANNEL_MAP[discord_id] = slack_id

# Slack setup
slack_app = AsyncApp(token=SLACK_TOKEN)

@slack_app.event("message")
async def handle_slack_message(event, say):
    if "bot_id" in event:
        return  # skip bot messages
    slack_channel = event["channel"]
    discord_channel_id = CHANNEL_MAP.get(slack_channel)
    if discord_channel_id:
        channel = bot.get_channel(int(discord_channel_id))
        if channel:
            user_id = event.get("user", "unknown")
            text = event.get("text", "")
            try:
                user_info = await slack_app.client.users_info(user=user_id)
                profile = user_info["user"]["profile"]
                display_name = profile.get("display_name_normalized") or profile.get("real_name_normalized") or user_id
            except Exception as e:
                print(f"Failed to fetch user info: {e}")
                display_name = user_id

            await channel.send(f"(Slack) {display_name}: {text}")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    discord_channel_id = str(message.channel.id)
    slack_channel_id = CHANNEL_MAP.get(discord_channel_id)
    if slack_channel_id:
        await slack_app.client.chat_postMessage(channel=slack_channel_id, text=f"(Discord) {message.author.name}: {message.content}")

    issuper = any(role.name == SUPERADMINROLE for role in message.author.roles)
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

    link_allowed = link_control.get(message.guild.id, True)
    if not link_allowed and ('https://' in message.content or 'http://' in message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention} links are currently disabled.")

    await bot.process_commands(message)

async def start_bridge():
    socket_handler = AsyncSocketModeHandler(slack_app, SLACK_APP_TOKEN)
    discord_task = asyncio.create_task(bot.start(token))
    slack_task = asyncio.create_task(socket_handler.start_async())
    await asyncio.gather(discord_task, slack_task)

if __name__ == "__main__":
    asyncio.run(start_bridge())
