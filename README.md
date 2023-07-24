# twitch-chat-logger
---
## Quick Start Guide
1. [Installing/Getting started](#installinggetting-started)
1. [Configuration](#configuration)
1. [Run the bot](#run-the-bot)
---
## Installing/Getting started

### Requirements
 - `twitchio`
 - `colorama`
 
### With git
```
git clone https://github.com/GameOneYT/twitch-chat-logger.git
cd twitch-chat-logger
pip install -r requirements.txt
```
---
## Configuration
### *Register Your Application* on **[Twitch dev](https://dev.twitch.tv/)**
### Specify the channels you want to track
```
channels = ["1channel", "2channel", "3channel"]
```
> No limit, but i recommend no more than 8
### Specify your `token`, `client_id` and `nick`
> `token` from **[Twitch token generator](https://twitchtokengenerator.com/)**

> `client_id` and `nick` from [Twitch dev](#register-your-application-on-twitch-dev)
```
token = "bot_token" 
client_id = "bot_client_id"
nick = "bot_nick"
```
---
## Run the bot
### Simply use: `python twitch-chat-logger.py`
You should then have the `chatlog.db` (SQLite database) in your folder.

> To view it you will need a program to view SQLite databases, I recommend [DB Browser for SQLite](https://sqlitebrowser.org/)
