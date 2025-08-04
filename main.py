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

    elif message.content.startswith("delete"):
        category_name = message.content.split(" ", 1)[1]
        category = discord.utils.get(message.guild.categories, name=category_name)

        await message.channel.send("Are you sure you want to remove this category? (yes/no)")
        confirm = await bot.wait_for("message", check=lambda m: m.author == message.author and m.channel == message.channel)
        if confirm.content.lower() == "yes" and category:
            for ch in category.channels:
                await ch.delete()
            await discord.utils.get(message.guild.roles, name=f"{category_name} {MENTORROLE}").delete()
            await discord.utils.get(message.guild.roles, name=category_name).delete()
            await category.delete()

    elif message.content.startswith("remove"):
        role_name = message.content.split(" ", 1)[1]
        role = discord.utils.get(message.guild.roles, name=role_name)

        await message.channel.send("Are you sure you want to remove the role? (yes/no)")
        confirm = await bot.wait_for("message", check=lambda m: m.author == message.author and m.channel == message.channel)
        if confirm.content.lower() == "yes":
            for member in message.guild.members:
                if role in member.roles:
                    await member.remove_roles(role)

@bot.command()
async def Create(ctx, *, name):
    if ctx.channel.name != "admin":
        await ctx.send("Wrong channel")
        return

    category = ctx.channel.category
    if category and any(ch.name == name for ch in category.text_channels):
        await ctx.send(f"{name} already exists!")
        return

    await ctx.guild.create_text_channel(name, category=category)
    await ctx.send(f"{name} created")

@bot.command()
async def Delete(ctx, *, name):
    if ctx.channel.name != "admin":
        await ctx.send("Wrong channel")
        return

    category = ctx.channel.category
    for ch in category.text_channels:
        if ch.name == name:
            await ch.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")

@bot.command()
async def links(ctx, setting: str):
    if ctx.channel.name != "admin":
        await ctx.send("Wrong channel")
        return

    link_control[ctx.guild.id] = setting.lower() == "on"
    await ctx.send(f"Links have been turned {'on' if setting.lower() == 'on' else 'off'}.")

@bot.command()
async def Clear(ctx, amount: str):
    if amount.lower() == "all":
        await ctx.channel.purge()
        return

    if not amount.isdigit():
        await ctx.send("Please enter a whole number e.g (!clear 100) or use 'all.'")
        return

    count = int(amount)
    if count == 0:
        await ctx.send("Please enter a number greater than 0.")
    else:
        await ctx.channel.purge(limit=count + 1)

async def start_bridge():
    socket_handler = get_socket_handler(SLACK_APP_TOKEN)
    discord_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    slack_task = asyncio.create_task(socket_handler.start_async())
    await asyncio.gather(discord_task, slack_task)

if __name__ == "__main__":
    asyncio.run(start_bridge())
