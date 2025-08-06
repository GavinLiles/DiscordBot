#Holds all the discord bot commands
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import tomllib
import tomli_w
import SuperAdmin
from locking import group_tokens_lock, channel_map_lock
import time
import datetime
import asyncio

lock = asyncio.Lock()

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
async def DeleteCategory(ctx, message, bot, MENTORROLE):
    if ctx.channel.name != 'superadminchat':
        await ctx.send("This command must be used in the #superadminchat channel.")
        return

    for category in ctx.guild.categories:
        if message.strip().lower() == str(category).strip().lower():
            await ctx.send(f"Are you sure you want to delete the category '{message}'? (yes/no)")
            confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

            if confirm.content.strip().lower() == "yes":
                success, msg = await delete_group_category(ctx.guild, message.strip(), MENTORROLE)
                await ctx.send(msg)
                return
            else:
                await ctx.send("Deletion cancelled.")
                return

    await ctx.send("No matching category found.")


#revokes a specific role from everyone
async def RevokeRoles(ctx, message, bot):
    if ctx.channel.name == 'superadminchat':
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
    if ctx.channel.name != 'admin':
        await ctx.send("This command must be used in the #admin channel.")
        return
    if member is None:
        await ctx.send("Please mention a member to remove roles from.")
        return
    if member == ctx.author:
        await ctx.send("You cannot remove yourself.")
        return
    if not group_names:
        await ctx.send("Please specify a role.")
        return


    role = discord.utils.get(ctx.guild.roles, name=group_names)
    if role:
        try:
            await member.remove_roles(role)
            await ctx.send(f"{member.mention} was removed from {group_names}.")
        except discord.Forbidden:
            await ctx.send(f"Don't have permission to remove {role.name}.")
        except discord.HTTPException as e:
            await ctx.send(f"Error removing {role.name}: {e}")
    else:
        await ctx.send(f"Group '{group_names}' not found.")

async def GetTokens(ctx, *, group_name):
    # must be used in superadminchat channel
    if ctx.channel.name != "superadminchat":
        await ctx.send("This command must be used in the #superadminchat channel.")
        return

    tokens_file = os.getenv("TOKENS", "group_tokens.toml")

    try:
        # lock token file access
        async with group_tokens_lock:
            # try to open and load the file
            with open(tokens_file, "rb") as f:
                token_data = tomllib.load(f)

        # get group entry
        group = token_data.get(group_name)
        if not group:
            await ctx.author.send(f"No token group found with the name '{group_name}'.")
            return

        # extract token info
        tokens_list = group.get("tokens", [])
        used_list = group.get("used", [])
        roles_list = group.get("roles", [])

        if not tokens_list:
            await ctx.author.send(f"No tokens exist for the group '{group_name}'.")
            return

        # format output lines
        lines = []
        for i, token in enumerate(tokens_list):
            role = roles_list[i].capitalize()
            status = "Used" if used_list[i] else "Unused"
            lines.append(f"{i + 1}. {token} - {role} - {status}")

        # send tokens in chunks to avoid a stoppage
        chunk_size = 25
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i + chunk_size]
            await ctx.author.send("\n".join(chunk))

        await ctx.send("Token list has been sent to your direct messages.")

    except FileNotFoundError:
        await ctx.author.send("Token file not found.")
    except Exception as e:
        await ctx.send("An error occurred while retrieving the tokens.")
        print(f"[ERROR] GetTokens: {e}")

async def delete_group_category(guild, category_name, MENTORROLE):
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        return False, "Category not found."

    deleted_channel_ids = [str(ch.id) for ch in category.channels]
    for ch in category.channels:
        await ch.delete()
    await category.delete()

    # Delete associated roles
    mentor_role_name = f"{category_name} {MENTORROLE}"
    user_role_name = category_name

    mentor_role = discord.utils.get(guild.roles, name=mentor_role_name)
    user_role = discord.utils.get(guild.roles, name=user_role_name)

    if mentor_role:
        await mentor_role.delete()
    if user_role:
        await user_role.delete()

    # Delete from group token file
    await SuperAdmin.delete_group_tokens(category_name)

    # Clean up Slack channel map
    slack_map_path = "channel_map.toml"
    if os.path.exists(slack_map_path):
        async with channel_map_lock:
            with open(slack_map_path, "rb") as f:
                data = tomllib.load(f)

            original = dict(data.get("channels", {}))
            updated = {k: v for k, v in original.items() if v not in deleted_channel_ids and k not in deleted_channel_ids}

            if updated != original:
                with open(slack_map_path, "wb") as f:
                    f.write(tomli_w.dumps({"channels": updated}).encode("utf-8"))

    return True, f"Category '{category_name}' and all associated resources were deleted."

async def CreateAssignment(Scheduled_Assignments, file, assignment, group, ctx, bot, channel):
    #check if group already has assignment with that name
    if await CheckDuplicate(channel, Scheduled_Assignments, assignment, group, bot):
        return
    #ask user for given time and 
    await ctx.send("Select time as MM/DD/YYYY HH:MM (2:30 pm should be 14:30)")
    confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
    #try if given valid date and time
    try:
        date_object = datetime.datetime.strptime(confirm.content, '%m/%d/%Y %H:%M')
    except:
        await ctx.send("Invalid time given")
    #check if assigned time isn't before current time
    if(date_object <= datetime.datetime.now()):
        await ctx.send("That is too soon")
        return
    FormalDate= date_object.strftime('%B %d, %Y at %I:%M %p')
    #write task data into file
    with open(file, 'a') as f:
        f.write(f"{assignment},{group},{confirm.content},{channel}\n")
    #let user know assignment is assigned
    await ctx.send(f"Assignment {assignment} is now set due on {date_object.strftime('%B %d, %Y at %I:%M %p')}")

    if group == 'all':
        for Category in ctx.guild.categories:
            if Category.name != 'SuperAdmin' and Category.name != 'Text Channels':
                Channel = discord.utils.get(Category.channels, name = 'general')
                Target_Role = discord.utils.get(ctx.guild.roles, name = str(Category.name))
                await Channel.send(f"{Target_Role.mention} {assignment} has been assigned. Due Date is {FormalDate}")
    else:
        Category = discord.utils.get(ctx.guild.categories, name=group)
        Channel = discord.utils.get(Category.channels, name = 'general')
        Target_Role = discord.utils.get(ctx.guild.roles, name = group)
        await Channel.send(f"{Target_Role.mention} {assignment} has been assigned. Due Date is {FormalDate}")
    #assignments.append({'assignment': assignment, 'date': date_object, 'FormalDate': date_object.strftime('%B %d, %Y at %I:%M %p'), 'position': len(assignments)-1})
        
    

    task = asyncio.create_task(PrintReminders(Scheduled_Assignments, assignment, date_object, channel, group, file, bot))
    Scheduled_Assignments.append([task, assignment, group, FormalDate])

async def CheckDuplicate(channel, Scheduled_Assignments, assignment, group,bot):
    #do if statment for superadminchat
    for x in Scheduled_Assignments:
        if x[1] == assignment and (x[2] == group):
            channel = await bot.fetch_channel(channel)
            await channel.send("Your group is already assigned an assignment called {assignment}")
            return True
    return False



#sends reminders to group(s) about due date
async def PrintReminders(Scheduled_Assignments, assignment, date_object, channel, group, file, bot):
    #get channel id
    channel = await bot.fetch_channel(channel)
    #get guild
    guild = channel.guild
    try:
        #create loop that goes on until the assignment date - current time is 0 or less
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        while((date_object - now).total_seconds() > 0):
            #if exactly 1 day left
            if int((date_object - now).total_seconds() // 60) == 1440:
                if group == 'all':
                    for category in guild.categories:
                        print(category.name)
                        if category.name != 'SuperAdmin' and category.name != 'Text Channels':
                            Channel = discord.utils.get(category.channels, name = 'general')
                            print("check1")
                            Target_Role = discord.utils.get(guild.roles, name = str(category.name))
                            print(category.name)
                            await Channel.send(f"{Target_Role.mention} {assignment} is due in 1 day!!!")

                else: 
                    await channel.send(f"{assignment} is due in 1 day!!!")
                    #if one hour remains
            if int((date_object - now).total_seconds() // 60) == 60:
                if group == 'all':
                    for category in guild.categories:
                            print(category.name)
                            if category.name != 'SuperAdmin' and category.name != 'Text Channels':
                                Channel = discord.utils.get(category.channels, name = 'general')
                                print("check1")
                                Target_Role = discord.utils.get(guild.roles, name = str(category.name))
                                print(category.name)
                                await Channel.send(f"{Target_Role.mention} {assignment} is due in 1 hour!!!")
                else:
             
                    await channel.send(f"{assignment} is due in 1 hour!!!")
            #make this function sleep for a minute
            await asyncio.sleep(60)
            #get current time
            now = datetime.datetime.now().replace(second=0, microsecond=0)
        #this will remove task data from the file and list
        for x in range(len(Scheduled_Assignments)):
            async with lock:
                if Scheduled_Assignments[x][1] == assignment and Scheduled_Assignments[x][2] == group:
                    Scheduled_Assignments.pop(x)
                    list = []
                    with open(file, 'r') as f:
                        for line in f:
                            x = line.strip()
                            x = x.split(',')
                            
                            if not (x[0] == assignment and x[1] == group):
                                list.append(line)
                    with open(file, 'w') as f:
                        for line in list:
                            f.write(f'{line}')
                    return
    except asyncio.CancelledError:
        return
    #This will show all assignment's related to the group
async def ViewAssignments(ctx, Scheduled_Assignments):
    #If running in SuperAdmin, check all assignments
    if ctx.channel.category.name == 'SuperAdmin':
        allprojects = ''
        groupprojects = ''
        for x in Scheduled_Assignments:
            
            
            if x[2] == 'all':
                allprojects += f'{x[1]} is due on {x[3]}\n'
            else:
                groupprojects += f'{x[2]} has {x[1]} due on {x[3]}\n'
        message = ''
        message += allprojects + groupprojects
        await ctx.send(message)
    #Check only assignments related to said group
    else:       
        message = "---Due Assignments---\n"
        assignments = ''
        for x in Scheduled_Assignments:
            if x[2] == ctx.channel.category.name or x[2] == 'all':
                assignments += f'{x[1]} is due on {x[3]}\n'
        if assignments == '':
            message = "Your group has no assignments!\n"
        else:
            message += assignments
        await ctx.send(message)
#This will remove an assignment and let the group(s) know
async def CancelAssignment(ctx, message, Scheduled_Assignments, file, bot):
    #Don't run if not in admin or SuperAdmin
    if ctx.channel.name != 'admin' and ctx.channel.category.name != 'SuperAdmin':
        return
    #if in SuperAdmin, is it global or for a specific group
    if ctx.channel.category.name == 'SuperAdmin':

        await ctx.channel.send("Insert either group name or global")
        #get user input
        confirm = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        print(confirm.content)
        if confirm.content.strip().lower() == 'global':
            
            group = 'all'
            message = 'Global assignment: ' + message
        else:
            group = confirm.content

    else:
        group = ctx.channel.category.name
    try:
        #go through each task info
        for x in range(len(Scheduled_Assignments)):
            async with lock:
                #if found remove from list
                if Scheduled_Assignments[x][1] == message and Scheduled_Assignments[x][2] == group:                
                    Scheduled_Assignments[x][0].cancel()
                    Scheduled_Assignments.pop(x)
                    
                    #let group(s) know about assignment cancel
                    if group == 'all':
                        for Category in ctx.guild.categories:
                        
                            if Category.name != 'SuperAdmin' and Category.name != 'Text Channels':
                                Channel = discord.utils.get(Category.channels, name = 'general')
                                Target_Role = discord.utils.get(ctx.guild.roles, name = str(Category.name))
                                await Channel.send(f"{Target_Role.mention} {message} has been canceled!") 
                    else:    
                        Category = discord.utils.get(ctx.guild.categories, name=group)
                        Channel = discord.utils.get(Category.channels, name = 'general')
                        Target_Role = discord.utils.get(ctx.guild.roles, name = group)
                        await ctx.send(f"{message} has been canceled!")
                        await Channel.send(f"{Target_Role.mention} {message} has been canceled!")
                    #Get all task data from file except current task and write to file with new data
                    list = []
                    with open(file, 'r') as f:
                        for line in f:
                            x = line.strip()
                            x = x.split(',')
                            if not ((x[0] == message) and x[1] == group):
                                list.append(line)
                    with open(file, 'w') as f:
                        for line in list:
                            f.write(f'{line}')
                    return
        if ctx.channel.category.name == 'SuperAdmin':
            await ctx.send(f"Either {message} isn't real or you specified the wrong group")
        else:
            await ctx.send(f"{message} assignment wasn't found")
    except:   
        #If file doesn't exist
        await ctx.send(f"{message} does not exist")
#this creates the assignments from a file
async def AssignmentFile(file, Scheduled_Assignments, bot):
    try:
        with open(file, 'r') as f:
            for line in f:
                line = line.strip()
                line = line.split(',')
                assignment, group, date_object, channel = line
                date_object = datetime.datetime.strptime(date_object, '%m/%d/%Y %H:%M')
                FormalDate= date_object.strftime('%B %d, %Y at %I:%M %p')
                task = asyncio.create_task(PrintReminders(Scheduled_Assignments, assignment, date_object, channel, group, file, bot))
                Scheduled_Assignments.append([task, assignment, group, FormalDate])
                

    except:
        return
