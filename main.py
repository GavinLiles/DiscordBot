import os
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import SuperAdmin
import Commands
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

    link_setting = link_control.get(message.guild.id, {})
    if any(scheme in message.content for scheme in ('http://', 'https://')):
        for role in message.author.roles:
            if link_setting.get(role.id) is False:
                try:
                    await message.delete()
                    warning = f"{message.author.mention}, links are currently disabled for your role '{role.name}'."
                    await message.channel.send(warning, delete_after=5)
                except Exception as e:
                    print(f"Error deleting message or sending warning: {e}")
                break

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
@commands.has_any_role("SuperAdmin")
async def Remove(ctx, member: discord.Member = None, *, group_names = None):
    await Commands.Remove(ctx, member, group_names=group_names)

@bot.command()
@commands.has_any_role("SuperAdmin")
async def Links(ctx, role_name: str, setting: str):
    await Commands.Links(ctx, link_control, role_name, setting)

# SuperAdmin and Mentor commands
@bot.command()
@commands.has_any_role("SuperAdmin", "MENTORROLE")
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


async def start_bridge():
    socket_handler = get_socket_handler(SLACK_APP_TOKEN)
    discord_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    slack_task = asyncio.create_task(socket_handler.start_async())
    await asyncio.gather(discord_task, slack_task)

if __name__ == "__main__":
    asyncio.run(start_bridge())
