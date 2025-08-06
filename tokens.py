import os
import tomllib
import tomli_w
import discord
import asyncio
from locking import group_tokens_lock

TOKENS_FILE = os.getenv("TOKENS", "group_tokens.toml")

async def process_token(message: discord.Message, mentor_role_label: str):

    try:
        # get the tokens from the file
        async with group_tokens_lock:
            with open(TOKENS_FILE, "rb") as infile:
                token_data = tomllib.load(infile)

        #the token the user entered and if it was found
        token_input = message.content.strip()
        matched = False

        #go through all the groupd and thier tokens looking for the token entered by the user
        for group_name, group_info in token_data.items():
            tokens = group_info.get("tokens", [])
            used = group_info.get("used", [])
            roles = group_info.get("roles", [])
            #if we find the token then chekc it has been used if not assign the role assoicated with that token
            if token_input in tokens:
                index = tokens.index(token_input)

                if used[index]:
                    await ephemeral_reply(message, "That token has already been used.")
                    return

                # assign the role for student
                group_role = discord.utils.get(message.guild.roles, name=group_name)
                if group_role:
                    await message.author.add_roles(group_role)
                else:
                    await ephemeral_reply(message, f"The role '{group_name}' was not found.")
                    return

                # if its a mentor token assign the mentor role
                if roles[index].lower() == "mentor":
                    mentor_role_name = f"{group_name} {mentor_role_label}"
                    mentor_role = discord.utils.get(message.guild.roles, name=mentor_role_name)
                    if mentor_role:
                        await message.author.add_roles(mentor_role)
                    else:
                        await ephemeral_reply(message, f"The mentor role '{mentor_role_name}' was not found.")

                # mark the token as used and rewrite to the file
                token_data[group_name]["used"][index] = True
                async with group_tokens_lock:
                    with open(TOKENS_FILE, "rb") as f:
                        token_data = tomllib.load(f)

                    with open(TOKENS_FILE, "wb") as f:
                        f.write(tomli_w.dumps(token_data).encode("utf-8"))

                matched = True
                await ephemeral_reply(message, f"You have been added to the group: {group_name}")
                break

        if not matched:
            await ephemeral_reply(message, "Invalid token. Please try again.")

    except Exception as e:
        print(f"[ERROR] Token processing failed: {e}")
        await ephemeral_reply(message, "An error occurred while processing your token.")

    finally:
        try:
            await message.delete()
        except:
            pass


async def ephemeral_reply(message: discord.Message, content: str):
    try:
        reply = await message.channel.send(f"{message.author.mention} {content}")
        await reply.delete(delay=10)
    except:
        pass
