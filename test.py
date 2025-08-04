from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv

load_dotenv()
SLACK_TOKEN = os.getenv('SLACK_TOKEN')        # xoxb-...
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')  # xapp-...

app = App(token=SLACK_TOKEN)

@app.event("app_mention")
def mention_handler(body, say):
    say("👋 Hello, world! I got your mention!")

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
