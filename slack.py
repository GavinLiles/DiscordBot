# slack.py
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

SLACK_APP = None
SOCKET_HANDLER = None

def init_slack_app(slack_token, bot, channel_map):
    global SLACK_APP

    SLACK_APP = AsyncApp(token=slack_token)

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

def get_slack_app():
    return SLACK_APP

def get_socket_handler(app_token):
    global SOCKET_HANDLER
    SOCKET_HANDLER = AsyncSocketModeHandler(SLACK_APP, app_token)
    return SOCKET_HANDLER
