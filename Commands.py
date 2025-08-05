#Holds all the discord bot commands
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import tomllib
import tomli_w
import SuperAdmin
#Creates a Voice channel
async def CreateTC(ctx, name):
    #do nothing if channel isn't admin
    if ctx.channel.name != "admin":
        return
    #set category to current category
    category = ctx.channel.category
    #check each channel if name exists and return if true
    if category and any(ch.name == name for ch in category.text_channels):
        await ctx.send(f"{name} already exists!")
        return
    #create channel
    await ctx.guild.create_text_channel(name, category=category)
    await ctx.send(f"{name} created")
#Deletes a text channel
async def DeleteTC(ctx, name):
    #do nothing and return if not in admin channel
    if ctx.channel.name != "admin":
        return
    #set category to current category
    category = ctx.channel.category
    #go through each text channel. If channel name matches name, delete channel and return
    for ch in category.text_channels:
        if ch.name == "general" or ch.name == "admin":
            ctx.send(f"{name} is a protected channel")
        elif ch.name == name:
            await ch.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")
#creates a voice channel
async def CreateVC(ctx, name):
    if ctx.channel.name != "admin":
        return

    category = ctx.channel.category
    if category and any(ch.name == name for ch in category.voice_channels):
        await ctx.send(f"{name} already exists!")
        return

    await ctx.guild.create_voice_channel(name, category=category)
    await ctx.send(f"{name} created")
#Deletes a voice channel
async def DeleteVC(ctx, name):
    if ctx.channel.name != "admin":
        return

    category = ctx.channel.category
    for ch in category.voice_channels:
        if ch.name == name:
            await ch.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")
    
#This will turn links on or off for roles
async def Links(ctx, link_control,role_name:str,setting: str):
    if ctx.channel.name != 'superadminchat':
        await ctx.send("Wrong channel")
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    setting = setting.lower()
    if not role:
        await ctx.send(f"Role '{role_name}' not found.")
        return
    if setting not in ['on', 'off']:
        await ctx.send("Invalid setting. Use !Links role_name on|off.")
        return
    if ctx.guild.id not in link_control:
        link_control[ctx.guild.id] = {}
    link_control[ctx.guild.id][role.id] = (setting == 'on')

#This will delete a certain amount or all messages in a channel
async def Clear(ctx, amount : str):
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

#deletes a category, including the channels and roles connected to said category
import SuperAdmin  # Ensure this is at the top of your file

async def DeleteCategory(ctx, message, bot, MENTORROLE):
    if str(ctx.channel) != 'superadminchat':
        return

    for category in ctx.guild.categories:
        if message.strip().lower() == str(category).strip().lower():
            await ctx.send(f"Are you sure you want to delete the category '{message}'? (yes/no)")

            confirm = await bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )

            if confirm.content.strip().lower() == "yes":
                deleted_channel_ids = [str(ch.id) for ch in category.channels]  # Save IDs before deleting

                # Delete all channels inside the category
                for ch in category.channels:
                    await ch.delete()

                # Delete the category itself
                await category.delete()

                try:
                    # Delete associated roles
                    mentor_role_name = f"{message} {MENTORROLE}"
                    user_role_name = message

                    mentor_role = discord.utils.get(ctx.guild.roles, name=mentor_role_name)
                    user_role = discord.utils.get(ctx.guild.roles, name=user_role_name)

                    if mentor_role:
                        await mentor_role.delete()
                        print(f"Deleted mentor role: {mentor_role_name}")
                    else:
                        print(f"Mentor role not found: {mentor_role_name}")

                    if user_role:
                        await user_role.delete()
                        print(f"Deleted user role: {user_role_name}")
                    else:
                        print(f"User role not found: {user_role_name}")

                    # Delete group tokens
                    category_name = message.strip()
                    SuperAdmin.delete_group_tokens(category_name)
                    print(f"Group tokens deleted for: {category_name}")

                    # Remove Slack channel mappings
                    slack_map_path = "channel_map.toml"
                    if os.path.exists(slack_map_path):
                        with open(slack_map_path, "rb") as f:
                            data = tomllib.load(f)

                        original = dict(data.get("channels", {}))
                        updated = {k: v for k, v in original.items() if v not in deleted_channel_ids and k not in deleted_channel_ids}

                        if updated != original:
                            with open(slack_map_path, "wb") as f:
                                f.write(tomli_w.dumps({"channels": updated}).encode("utf-8"))
                            print(f"Removed Slack mappings for deleted Discord channels in '{message}'")

                    await ctx.send(f"Category '{message}' and all associated resources were deleted.")
                    return

                except Exception as e:
                    print(f"Error while deleting roles or tokens: {e}")
                    await ctx.send(f"Error during deletion: {e}")
                    return

            else:
                await ctx.send("Deletion cancelled.")
                return

    await ctx.send("No matching category found.")

        
#revokes a specific role from everyone
async def RevokeRoles(ctx, message, bot):
    if str(ctx.channel) == 'superadminchat':
        try:
            role = discord.utils.get(ctx.guild.roles, name=message)

            await ctx.channel.send("Are you sure you want to remove the role? (yes/no)")
            confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            if confirm.content.lower() == "yes":
                for member in ctx.guild.members:
                    if role in member.roles:
                        await member.remove_roles(role)
        except:
            print(f"role {message} not found")

#Removes specified roles from a member.
async def Remove(ctx, member: discord.Member=None, *, group_names=None):
    if ctx.channel.name != 'superadminchat':
        await ctx.send("Wrong channel")
        return
    if member is None:
        await ctx.send("Please mention a member to remove roles from.")
        return
    if member == ctx.author:
        await ctx.send("You cannot remove yourself.")
        return
    if not group_names:
        await ctx.send("Please specify one or more group names.")
        return

    group_list = group_names.split()

    for group in group_list:
        role = discord.utils.get(ctx.guild.roles, name=group)
        if role:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                await ctx.send(f"Don't have permission to remove {role.name}.")
            except discord.HTTPException as e:
                await ctx.send(f"Error removing {role.name}: {e}")
        else:
            await ctx.send(f"Group '{group}' not found.")
