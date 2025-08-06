import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import SuperAdmin
import Commands
import re
import tokens
from slack import (
    init_slack_app,
    get_slack_app,
    get_socket_handler,
    get_channel_map,
    load_channel_map,
)


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SUPERADMINCHAT = os.getenv("SUPERADMINCHAT", "SUPERADMINCHAT")
SUPERADMINROLE = os.getenv("SUPERADMINROLE", "SuperAdmin")
MENTORROLE = os.getenv("MentorRole", "Mentor")
TOKENSCHANNEL = os.getenv("TOKENSCHANNEL", "TokensChannel")
TOKENS = os.getenv("TOKENS", "group_tokens.toml")

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

    if message.channel.name.lower() == TOKENSCHANNEL.lower():
        await tokens.process_token(message, MENTORROLE)

    if message.channel.name == SUPERADMINCHAT and any(role.name == SUPERADMINROLE for role in message.author.roles):
        await handle_superadmin_commands(message)

    if(islink(message.content)):
        perms = message.channel.permissions_for(message.author)
        if not perms.embed_links:
            try:
                await message.delete()
            except:
                pass

    await bot.process_commands(message)

async def handle_superadmin_commands(message):
    if message.attachments:
        await SuperAdmin.process_tml(bot, message, SUPERADMINCHAT, SUPERADMINROLE, MENTORROLE)

# SuperAdmin-only commands
@bot.command()
@commands.has_any_role("SuperAdmin")
async def DeleteCategory(ctx, *, message):
    await Commands.DeleteCategory(ctx, message, bot, MENTORROLE)

@bot.command()
@commands.has_any_role("SuperAdmin")
async def RevokeRoles(ctx, *, message):
    await Commands.RevokeRoles(ctx, message, bot)

@bot.command()
async def Remove(ctx, member: discord.Member = None, *, group_names = None):
    await Commands.Remove(ctx, member, group_names=group_names)

@bot.command()
async def Links(ctx, setting: str):
    await Commands.Links(ctx, setting)

# SuperAdmin and Mentor commands
@bot.command()
async def Clear(ctx, amount: str):
    await Commands.Clear(ctx, amount)

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
async def GetTokens(ctx, *, group_name):
    await Commands.GetTokens(ctx, group_name=group_name)

def islink(link) -> bool: 
    link_regex = re.compile(
        r"""(?xi)
        \b(
            (?:[a-z][a-z0-9+\-.]*://)      # any scheme:// (http, https, ftp, etc.)
            | www\d{0,3}[.]                # www., www1.
            | [a-z0-9.\-]+\.[a-z]{2,}      # bare domain (example.com)
        )
        """, re.VERBOSE | re.IGNORECASE
    )
    return bool(link_regex.search(link))

async def start_bridge():
    socket_handler = get_socket_handler(SLACK_APP_TOKEN)
    discord_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    slack_task = asyncio.create_task(socket_handler.start_async())
    await asyncio.gather(discord_task, slack_task)

if __name__ == "__main__":
    asyncio.run(start_bridge())
