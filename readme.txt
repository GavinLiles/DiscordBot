==============================
Project Title: 
- Discord–Slack Bridge Bot
==============================

Description:
- This bot syncs messages between Discord and Slack, automates the creation of group structures (roles, categories, channels), and manages token-based access for users (e.g., mentors and students).
- It’s built using Python with support for discord.py, slack_bolt, and TOML configuration files for persistent storage and setup automation.

Features:
- Slack to Discord Message Relay:
    - Bi-directional message sync between mapped Slack and Discord channels.
    - Maintains mappings using channel_map.toml.

- TOML-Based Group Setup:
    - Upload .toml files to auto-create structured groups with text/voice channels, roles, and permissions.
    - Supports merge/replace/skip logic when conflicts arise.

- Token System for Access:
    - Students and mentors submit tokens in Discord to automatically receive roles.
    - Tokens are tracked and marked as used after assignment.

- Admin Commands:
    - !CreateTC, !DeleteVC, !Clear, !RevokeRoles, !Links on|off, !Remove, !DeleteCategory, etc.
    - Protected channel names like "admin" and "superadminchat" ensure commands are restricted.
    - !help gives all Commands.

- File Locking:
    - Uses asyncio.Lock to prevent concurrent write issues in TOML files.

Installation:
- Python version: 3.13.5
- Install dependencies with:
    pip install discord.py slack_bolt python-dotenv tomli tomli-w

How to Run the Bot:
1. Create a .env file with the following variables:
    DISCORD_TOKEN=your_discord_bot_token
    SLACK_TOKEN=your_slack_bot_token
    SLACK_APP_TOKEN=your_slack_app_token
    SUPERADMINCHAT=superadminchat
    SUPERADMINROLE=SuperAdmin
    MentorRole=Mentor
    TOKENSCHANNEL=tokenschannel
    TOKENS=group_tokens.toml

2. Run the bot with:
    python main.py

3. Slack and Discord will begin syncing messages and listening for TOML or token actions.

File Structure:
- main.py              : Launches Discord and Slack bots, manages event handling
- slack.py             : Handles Slack events and channel mapping
- SuperAdmin.py        : Processes TOML uploads for automated group creation
- Commands.py          : Discord admin commands for roles, channels, and token management
- tokens.py            : Handles token-based role assignment in Discord
- locking.py           : Defines async locks to prevent file conflicts
- channel_map.toml     : Stores Slack <-> Discord channel ID mappings
- group_tokens.toml    : Stores generated access tokens for group membership
- test2.toml / TEST.toml: Sample group setup files
- .env                 : Environment variables (not committed to source control)

Credits:
Yarely Torres
Gavin Liles
Ryan Franscis

