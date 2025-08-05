import os
import tomllib
import logging
import asyncio
import discord

from discord.ext import commands
from dotenv import load_dotenv

import SuperAdmin
import Control
from slack import init_slack_app, get_slack_app, get_socket_handler, get_channel_map, load_channel_map
import Commands

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SUPERADMINCHAT = os.getenv("SUPERADMINCHAT", "SUPERADMINCHAT")
SUPERADMINROLE = os.getenv("SUPERADMINROLE", "SuperAdmin")
MENTORROLE = os.getenv("MentorRole", "Mentor")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
link_control = {}

logging.basicConfig(filename="discord.log", encoding="utf-8", level=logging.INFO)

load_channel_map()
slack_app = init_slack_app(SLACK_TOKEN, bot, get_channel_map())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    discord_channel_id = str(message.channel.id)
    slack_channel_id = get_channel_map().get(discord_channel_id)

    if slack_channel_id:
        await get_slack_app().client.chat_postMessage(
            channel=slack_channel_id,
            text=f"(Discord) {message.author.name}: {message.content}"
        )

    if message.channel.name == SUPERADMINCHAT and any(role.name == SUPERADMINROLE for role in message.author.roles):
        await handle_superadmin_commands(message)

    if not link_control.get(message.guild.id, True):
        if "http://" in message.content or "https://" in message.content:
            await message.delete()
            await message.channel.send(f"{message.author.mention} links are currently disabled.")

    await bot.process_commands(message)

async def handle_superadmin_commands(message):
    if message.attachments:
        await SuperAdmin.process_tml(message, SUPERADMINCHAT, SUPERADMINROLE, MENTORROLE)

#these are user input commands for SuperAdmin
@bot.command()
@commands.has_any_role("SuperAdmin")
async def DeleteCategory(ctx, *, message):
    await Commands.DeleteCategory(ctx, message, bot, MENTORROLE)
    
@bot.command()
@commands.has_any_role("SuperAdmin")
async def RevokeRoles(ctx, *, message):
    await Commands.RevokeRoles(ctx, message, bot)
    
#These are user input commands for both Mentors and SuperAdmin
@bot.command()
async def CreateTC(ctx, *, name):
    await Commands.CreateTC(ctx, name)

@bot.command()
async def DeleteTC(ctx, *, name):
    await Commands.DeleteTC(ctx, name)

@bot.command()
async def CreateVC(ctx, *, name):
    await Commands.CreateVC(ctx, name)

@bot.command()
async def DeleteVC(ctx, *, name):
    await Commands.DeleteVC(ctx, name)

@bot.command()
async def links(ctx, setting: str):
    await Commands.links(ctx, link_control, setting)

@bot.command()
@commands.has_any_role("SuperAdmin", "MENTORROLE")
async def Clear(ctx, amount: str):
    await Commands.Clear(ctx, amount)

async def start_bridge():
    socket_handler = get_socket_handler(SLACK_APP_TOKEN)
    discord_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    slack_task = asyncio.create_task(socket_handler.start_async())
    await asyncio.gather(discord_task, slack_task)

if __name__ == "__main__":
    asyncio.run(start_bridge())
