# Twitch Chat Logger <sub>client</sub>

## Quick Start Guide
1. [Installing/Getting started](#installinggetting-started)
1. [Configuration](#configuration)
1. [Run the bot](#run-the-bot)

## Installing/Getting started

### Python 3.10+

### Pip requirements
 - `websocket-client`
 - `colorama`
 - `rel`
 
### With git
``` bash
git clone https://github.com/GameOneDev/TCLc
cd TCLc
pip install -r requirements.txt
```

## Configuration
### Specify the channels you want to track
``` python
channels = ["1channel", "2channel", "3channel"]
```
> No limit, but i recommend < 8

## Run the bot
### Simply use: `python twitch-chat-logger.py`
You should then have the `chatlog.db` (SQLite database) in your folder.

> To view it, you will need a program to view SQLite databases, I recommend [DB Browser for SQLite](https://sqlitebrowser.org/)
