# slack.py
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
import tomli_w
import os
import tomllib
import asyncio
from locking import channel_map_lock

# Global instances for Slack app and socket handler
SLACK_APP = None
SOCKET_HANDLER = None

# Path to the local TOML file used for mapping Discord and Slack channels
CHANNEL_MAP_FILE = "channel_map.toml"
CHANNEL_MAP = {}

# Initializes the Slack app with the token and channels it should connect to in Discord
def init_slack_app(slack_token, bot, channel_map):
    global SLACK_APP

    SLACK_APP = AsyncApp(token=slack_token)

    # Looks for events from Slack, such as messages
    @SLACK_APP.event("message")
    async def handle_slack_message(event, say):
        if "bot_id" in event:
            return
        slack_channel = event["channel"]
        discord_channel_id = channel_map.get(slack_channel)
        if discord_channel_id:
            channel = bot.get_channel(int(discord_channel_id))
            if channel:
                user_id = event.get("user", "unknown")
                text = event.get("text", "")
                try:
                    user_info = await SLACK_APP.client.users_info(user=user_id)
                    profile = user_info["user"]["profile"]
                    display_name = profile.get("display_name_normalized") or profile.get("real_name_normalized") or user_id
                except Exception as e:
                    print(f"Failed to fetch user info: {e}")
                    display_name = user_id

                await channel.send(f"(Slack) {display_name}: {text}")

    return SLACK_APP

# Returns the initialized Slack app instance
def get_slack_app():
    return SLACK_APP

# Initializes and returns the Slack socket handler
def get_socket_handler(app_token):
    global SOCKET_HANDLER
    SOCKET_HANDLER = AsyncSocketModeHandler(SLACK_APP, app_token)
    return SOCKET_HANDLER

# Loads the existing channel mappings from the TOML file into memory
def load_channel_map():
    global CHANNEL_MAP
    if os.path.exists(CHANNEL_MAP_FILE):
        try:
            with open(CHANNEL_MAP_FILE, "rb") as f:
                config = tomllib.load(f)
                CHANNEL_MAP.clear()
                for slack_id, discord_id in config.get("channels", {}).items():
                    CHANNEL_MAP[slack_id] = discord_id
                    CHANNEL_MAP[discord_id] = slack_id  # Reverse mapping
        except Exception as e:
            print("Failed to reload channel map:", e)

# Returns the in-memory channel mapping dictionary
def get_channel_map():
    return CHANNEL_MAP

# Updates the TOML file and in-memory map to associate a Slack channel with a Discord channel
def update_channel_map(slack_id: str, discord_channel_id: str):
    if not slack_id or not discord_channel_id:
        return

    async def _update():
        async with channel_map_lock:
            try:
                # load the files
                if os.path.exists(CHANNEL_MAP_FILE):
                    with open(CHANNEL_MAP_FILE, "rb") as f:
                        data = tomllib.load(f)
                else:
                    data = {"channels": {}}
                # Add or update the Slack to Discord mapping
                data.setdefault("channels", {})
                data["channels"][slack_id] = discord_channel_id
                
                #write them back
                with open(CHANNEL_MAP_FILE, "wb") as f:
                    f.write(tomli_w.dumps(data).encode("utf-8"))

                # Update the live CHANNEL_MAP live
                CHANNEL_MAP[slack_id] = discord_channel_id
                CHANNEL_MAP[discord_channel_id] = slack_id

                print(f"Mapped Slack {slack_id} to Discord {discord_channel_id} (live update)")
            except Exception as e:
                print(f"Error writing to channel map: {e}")

    asyncio.create_task(_update())
