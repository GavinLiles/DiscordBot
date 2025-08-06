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
    if ctx.channel.name != "admin": #only allowing creation from 'admin' channel
        return
    
    category = ctx.channel.category

    #check each channel if name exists
    if category and any(ch.name == name for ch in category.text_channels):
        await ctx.send(f"{name} already exists!")
        return
    
    #create channel
    await ctx.guild.create_text_channel(name, category=category)
    await ctx.send(f"{name} created")

#Deletes a text channel
async def DeleteTC(ctx, name):
    if ctx.channel.name != "admin": # only allow deletion from 'admin' channel
        return
    
    protected_channels = ["general", "admin"]

    #set category to current category
    category = ctx.channel.category

    #go through each text channel. If channel name matches name, delete channel and return
    for txt_channel in category.text_channels:
        if txt_channel.name == name:

            if txt_channel.name in protected_channels:
                await ctx.send(f"{name} is a protected channel")
                return 
            
            await txt_channel.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")

#creates a voice channel
async def CreateVC(ctx, name):
    if ctx.channel.name != "admin":  # only allows creation of voice channel in 'admin channel 
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
    for voice_channel in category.voice_channels:

        if voice_channel.name == name:
            await voice_channel.delete()
            await ctx.send(f"{name} has been deleted")
            return

    await ctx.send("Channel does not exist")
    
#This will turn links on or off for roles
async def Links(ctx, setting: str):
    #the command is used only in the 'superadminchat' channel
    if ctx.channel.name != 'admin':
        return
    
      # try to find the role object by its name in the server
    category = ctx.channel.category
    role = discord.utils.get(ctx.guild.roles, name=category.name)
    setting = setting.lower()

    if not category:
        await ctx.send(f"Role '{category.name}' not found.")
        return
    if setting not in ['on', 'off']:
        await ctx.send("Invalid setting. Use !Links role_name on|off.")
        return
    perms = role.permissions
    perms.update(embed_links=(setting == 'on'))

     # initialize the dictionary for the guild in link_control if it doesn't exist yet
    try:
        await role.edit(permissions=perms)
        await ctx.send(f"`embed_links` permission has been set to **{setting}** for role '{category.name}'.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to edit that role.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
    

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
        return
    
    await ctx.channel.purge(limit=count + 1)

#deletes a category, including the channels and roles connected to said category
import SuperAdmin  # Ensure this is at the top of your file

async def DeleteCategory(ctx, message, bot, MENTORROLE):
    if str(ctx.channel) != 'superadminchat':
        await ctx.send("This command must be used in the #superadminchat channel.")
        return
    # Look for a category with the given name
    for category in ctx.guild.categories:
        if message.strip().lower() == str(category).strip().lower():
            await ctx.send(f"Are you sure you want to delete the category '{message}'? (yes/no)")
             # Wait for confirmation from the same user in the same channel
            confirm = await bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )

            if confirm.content.strip().lower() == "yes":
                 # Collect channel IDs before deleting 
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
    else:
        await ctx.send("This command must be used in the #superadminchat channel.")
        return

#Removes specified roles from a member.
async def Remove(ctx, member: discord.Member=None, *, group_names=None):
    #the command is only used in the superadminchat channel
    if ctx.channel.name != 'admin':
        await ctx.send("This command must be used in the #admin channel.")
        return
    # check if a member is mentioned
    if member is None:
        await ctx.send("Please mention a member to remove roles from.")
        return
    # prevent the command user from removing their own roles
    if member == ctx.author:
        await ctx.send("You cannot remove yourself.")
        return
    # check group names are provided
    if not group_names:
        await ctx.send("Please specify a role.")
        return

    
    # loop through each group and try to remove the corresponding role
    
    role = discord.utils.get(ctx.guild.roles, name=group_names)
    if role:
        try:
            await member.remove_roles(role)
            await ctx.send(f"{member.mention} was removed from {group_names}.")
        except discord.Forbidden:
                # handle case where bot lacks permission to remove the role
            await ctx.send(f"Don't have permission to remove {role.name}.")
        except discord.HTTPException as e:
            # any other API-related error
            await ctx.send(f"Error removing {role.name}: {e}")
    else:
        await ctx.send(f"Group '{group_names}' not found.")

async def GetTokens(ctx, *, group_name):
    if ctx.channel.name != "superadminchat":
        await ctx.send("This command must be used in the #superadminchat channel.")
        return
    # Load the token file path from environment or use default
    tokens_file = os.getenv("TOKENS", "group_tokens.toml")

    if not os.path.exists(tokens_file):
        await ctx.author.send("Token file not found.")
        return

    try:
        with open(tokens_file, "rb") as f:
            token_data = tomllib.load(f)
                # Get the token group by name

        # Get the token group by name
        group = token_data.get(group_name)
        if not group:
            await ctx.author.send(f"No token group found with the name '{group_name}'.")
            return

        tokens_list = group.get("tokens", [])
        used_list = group.get("used", [])
        roles_list = group.get("roles", [])

        if not tokens_list:
            await ctx.author.send(f"No tokens exist for the group '{group_name}'.")
            return
        # Format the token info
        lines = []
        for i, token in enumerate(tokens_list):
            role = roles_list[i].capitalize()
            status = "Used" if used_list[i] else "Unused"
            lines.append(f"{i + 1}. {token} - {role} - {status}")

        # Break into chunks to avoid Discord's message limit
        chunk_size = 25
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i + chunk_size]
            await ctx.author.send("\n".join(chunk))

        await ctx.send("Token list has been sent to your direct messages.")

    except Exception as e:
        await ctx.send("An error occurred while retrieving the tokens.")
        print(f"[ERROR] GetTokens: {e}")