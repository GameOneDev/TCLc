import sqlite3
import colorama
from colorama import Fore, Style
import random
import signal
import sys
import re
from packaging import version
import websocket
import rel
from datetime import datetime

channels = ["1channel", "2channel", "3channel"]
db_name = "chatlog.db"
save_interval = 60  # Save messages every 60 seconds
msg_per_sec_updater = 2  # Update msg/s every 2 seconds

debug = False


program_version = version.Version("0.1.2")  # Do NOT change


class Bot:
    def __init__(self):

        self.setup_bot()

    def db_initialize(self):
        self.cursor = None
        self.conn = None
        db_version = str(program_version)

        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "messages" ("msg_id"	TEXT,"timestamp"	TEXT,"streamer_id"	TEXT,"user_id"	INTEGER,"message"	TEXT, "deleted_time"	TEXT DEFAULT NULL, "sync_status"	INTEGER DEFAULT 0,PRIMARY KEY("msg_id"),FOREIGN KEY("user_id") REFERENCES "users"("user-id"));"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "settings" ("db_version"	TEXT);"""
        )
        self.cursor.execute(
            "INSERT OR IGNORE INTO settings(db_version) VALUES (?)", (db_version,)
        )

        self.cursor.execute('''ATTACH "user.db" AS "user"''')
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "user"."users" ("user_id"	INTEGER UNIQUE,"display_name"	TEXT,"last_update"	TEXT DEFAULT NULL,"color"	TEXT DEFAULT NULL,"first_seen"	TEXT DEFAULT NULL,"priority_update"	INTEGER DEFAULT 0, PRIMARY KEY("user_id"));"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "user"."bans" ("ban_id"	INTEGER,"user_id"	INTEGER,"ban_channel"	TEXT,"ban_duration"	TEXT,"timestamp"	TEXT,FOREIGN KEY("user_id") REFERENCES "users"("user_id"),FOREIGN KEY("ban_channel") REFERENCES "users"("user_id"),PRIMARY KEY("ban_id" AUTOINCREMENT));"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "user"."display_name_update" ("user_id"	INTEGER,"old_display_name"	TEXT,"timestamp"	TEXT, FOREIGN KEY("user_id") REFERENCES "users"("user_id"));"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "user"."color_update" ("user_id"	INTEGER,"timestamp"	TEXT,"old_color"	TEXT, FOREIGN KEY("user_id") REFERENCES "users"("user_id"));"""
        )

        self.cursor.execute(
            """CREATE TRIGGER IF NOT EXISTS "user"."update_display_name" BEFORE INSERT ON "users" FOR EACH ROW WHEN (EXISTS (SELECT 1 FROM users WHERE user_id = NEW.user_id) AND (SELECT display_name FROM users WHERE user_id = NEW.user_id) != NEW.display_name) BEGIN INSERT INTO "display_name_update"("user_id", "old_display_name", "timestamp") VALUES(NEW.user_id, (SELECT display_name FROM users WHERE user_id = NEW.user_id), datetime('now')); UPDATE "users" SET display_name = NEW.display_name WHERE user_id = NEW.user_id; END;"""
        )
        self.cursor.execute(
            """CREATE TRIGGER IF NOT EXISTS "user"."update_color" BEFORE INSERT ON "users" FOR EACH ROW WHEN (EXISTS (SELECT 1 FROM users WHERE user_id = NEW.user_id) AND (SELECT color FROM users WHERE user_id = NEW.user_id) != NEW.color) BEGIN INSERT INTO "color_update"("user_id", "timestamp", "old_color") VALUES(NEW.user_id, datetime('now'), (SELECT color FROM users WHERE user_id = NEW.user_id)); UPDATE "users" SET color = NEW.color WHERE user_id = NEW.user_id; END;"""
        )

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS "user"."settings" ("db_version"	TEXT);"""
        )
        self.cursor.execute(
            "INSERT OR IGNORE INTO user.settings(db_version) VALUES (?)", (db_version,)
        )

    def setup_bot(self):
        colorama.init()  # Initialize colorama

        print(f'{Fore.BLUE}{"#" * 30}')
        print(
            f"""{Fore.GREEN}
      _______ _____ _          
     |__   __/ ____| |         
        | | | |    | |     ___ 
        | | | |    | |    / __|
        | | | |____| |___| (__ 
        |_|  \_____|______\___|
                           
    Twitch Chat Logger (client) v.{program_version}
    
    """
        )
        print(f'{Fore.BLUE}{"#" * 30}{Style.RESET_ALL}')

        self.db_initialize()  # Initialize db

        self.msg_per_sec = 0
        self.channel_message_count = 0
        self.channel_colors = self.assign_colors_to_channels()
        self.last_save_time = datetime.now()
        self.max_msg_per_sec = 0
        self.last_avg = datetime.now()
        self.db_commit(silent=True)

        self.messages = []

    def assign_colors_to_channels(self):
        available_colors = [
            Fore.RED,
            Fore.GREEN,
            Fore.YELLOW,
            Fore.BLUE,
            Fore.MAGENTA,
            Fore.CYAN,
            Fore.LIGHTGREEN_EX,
            Fore.LIGHTBLUE_EX,
        ]
        random.shuffle(available_colors)
        return {
            channel: available_colors[i % len(available_colors)]
            for i, channel in enumerate(channels)
        }

    def calculate_gradient_color(self, count_per_sec):
        gradient_upper_limit = max(self.max_msg_per_sec, 1)  # Avoid division by zero
        normalized_value = (
            min(count_per_sec, gradient_upper_limit) / gradient_upper_limit
        )
        r = int((1 - normalized_value) * 255)
        g = int(normalized_value * 255)
        b = 0
        ansi_color = (
            16 + (36 * int(r / 255 * 5)) + (6 * int(g / 255 * 5)) + int(b / 255 * 5)
        )
        return f"\x1b[38;5;{ansi_color}m"

    def db_commit(self, silent=True):
        """Commit to db
        silent: Commit to db silently
        """

        if not silent:
            print(f'{Fore.BLUE}{"#" * 30}')
            print(f'{Fore.GREEN}{"DB updating..."}')

        self.conn.commit()

        if not silent:
            print(f'{Fore.BLUE}{"#" * 30}{Style.RESET_ALL}')

    # TODO:
    def fetch_user_data(self):
        return

    def handle_message(self, message):
        """Handle received message"""
        command = message["command"]
        if command == "PRIVMSG":
            self.handle_privmsg(message)
        elif command == "CLEARCHAT":
            self.handle_clearchat(message)
        elif command == "CLEARMSG":
            self.handle_clearmsg(message)
        # TODO:
        # elif command == "USERNOTICE":
        #     self.handle_usernotice(message)

    def handle_privmsg(self, message):
        username = message["username"]  # User username
        user_id = int(message["metadata"].get("user-id"))  # User id
        user_color = message["metadata"].get("color")  # User color
        enc_message = message["message"]  # User message
        message_id = message["metadata"].get("id")  # Message id
        channel = message["channel"]
        channel_id = int(message["metadata"].get("room-id"))  # Streamer channel id
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        current_time = datetime.now()
        # TODO: AntiSpam feature

        self.cursor.execute(
            "INSERT INTO messages(msg_id, timestamp, streamer_id, user_id, message) VALUES (?, ?, ?, ?, ?)",
            (message_id, timestamp, channel_id, int(user_id), enc_message),
        )
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, display_name, first_seen, color) VALUES (?, ?, ?, ?)",
            (
                user_id,
                username,
                timestamp,
                user_color,
            ),
        )

        self.channel_message_count += 1

        elapsed_time_msg = (current_time - self.last_avg).total_seconds()
        if elapsed_time_msg >= msg_per_sec_updater:
            self.msg_per_sec = self.channel_message_count / elapsed_time_msg
            self.channel_message_count = 0
            self.last_avg = current_time

        self.max_msg_per_sec = max(self.max_msg_per_sec, self.msg_per_sec)

        color_channel = self.channel_colors[channel]
        gradient_color_msg = self.calculate_gradient_color(self.msg_per_sec)

        print(
            f"{timestamp} {gradient_color_msg}({self.msg_per_sec:.2f} msg/s({self.max_msg_per_sec:.2f})) {color_channel}[{channel}] {username}: {enc_message}{Style.RESET_ALL}"
        )

        if (current_time - self.last_save_time).total_seconds() >= save_interval:
            self.db_commit(False if debug else True)
            self.last_save_time = current_time

    def handle_clearchat(self, message):
        username = message["target_user"]  # User username
        user_id = int(message["target_user_id"])  # User id
        channel = message["channel"]  # Streamer username
        channel_id = int(message["metadata"].get("room-id"))  # Streamer channel id
        ban_durtation = message["metadata"].get("ban-duration")  # Ban duration
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        color_channel = self.channel_colors[channel]

        self.cursor.execute(
            "INSERT OR IGNORE INTO 'user'.bans('user_id', 'ban_channel', 'ban_duration', 'timestamp') VALUES (?, ?, ?, ?)",
            (user_id, channel_id, ban_durtation, timestamp),
        )

        print(
            f"{timestamp} {color_channel}[{channel}] {Fore.RED}BAN: {color_channel}({username}) {Fore.RED}ON{color_channel}: {ban_durtation} sec {Style.RESET_ALL}"
        )

    def handle_clearmsg(self, message):
        username = message["metadata"].get("login")  # User username
        channel = message["channel"]  # Streamer username
        msg_id = message["metadata"]["target-msg-id"]
        message_text = message["message"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        color_channel = self.channel_colors[channel]

        self.cursor.execute(
            "UPDATE messages SET deleted_time = ? WHERE msg_id = ?", (timestamp, msg_id)
        )

        print(
            f"{timestamp} {color_channel}[{channel}]{Fore.RED} Msg deleted {color_channel}({username}): {message_text}{Style.RESET_ALL}"
        )


# WebSocket
def parse_twitch_message(raw_message):
    try:
        if raw_message.startswith("@"):
            metadata_part, user_info_and_message = raw_message.split(" ", 1)
        elif debug:
            print("Message format incorrect, unable to split metadata and user info.")
            return None

        # Parse metadata
        metadata = {}
        metadata_items = metadata_part[1:].split(";")
        for item in metadata_items:
            key, value = item.split("=", 1)
            metadata[key] = value

        if "PRIVMSG" in user_info_and_message:
            user_info_pattern = re.compile(
                r":(\w+)!(\w+)@(\w+)\.tmi\.twitch\.tv PRIVMSG #(\w+) :(.+)\r\n"
            )
            match = user_info_pattern.match(user_info_and_message)
            if match:
                command = "PRIVMSG"
                username = match.group(1)
                channel = match.group(4)
                message = match.group(5)
                return {
                    "metadata": metadata,
                    "username": username,
                    "command": command,
                    "channel": channel,
                    "message": message,
                }
            elif debug:
                print("User info and message format is incorrect.")
                return None

        if "CLEARCHAT" in user_info_and_message:
            user_info_pattern = re.compile(
                r":tmi\.twitch\.tv CLEARCHAT #(\w+) :(\w+)\r\n"
            )
            match = user_info_pattern.match(user_info_and_message)
            if match:
                command = "CLEARCHAT"
                channel = match.group(1)
                target_user = match.group(2)
                target_user_id = metadata.get("target-user-id")
                return {
                    "metadata": metadata,
                    "command": command,
                    "channel": channel,
                    "target_user": target_user,
                    "target_user_id": target_user_id,
                }
            elif debug:
                print("Clear chat format is incorrect.")
                return None

        if "CLEARMSG" in user_info_and_message:
            user_info_pattern = re.compile(
                r":tmi\.twitch\.tv CLEARMSG #(\w+) :(.+)\r\n"
            )
            match = user_info_pattern.match(user_info_and_message)
            if match:
                command = "CLEARMSG"
                channel = match.group(1)
                message = match.group(2)
                return {
                    "metadata": metadata,
                    "command": command,
                    "channel": channel,
                    "message": message,
                }
            elif debug:
                print("Clear message format is incorrect.")
                return None
        if debug:
            print("Unknown command or unsupported message type.")
        return None
    except Exception as e:
        if debug:
            print(f"Exception in parse_twitch_message: {e}")
        return None


def on_message(ws, message):
    if "PING :tmi.twitch.tv" in str(message):
        print(f'{Fore.BLUE}{"#" * 30}')
        ws.send("PONG")
        print(f"{Fore.GREEN}Twitch: PING <-> PONG")
        print(f'{Fore.BLUE}{"#" * 30}{Style.RESET_ALL}')
        return

    parsed_message = parse_twitch_message(message)

    if parsed_message:
        bot.handle_message(parsed_message)
    elif debug:
        print(f'{Fore.RED}{"#" * 30}')
        print(str(message))
        print(f'{Fore.RED}{"#" * 30}{Style.RESET_ALL}')


def on_error(ws, error):
    print(f'{Fore.RED}{"#" * 30}')
    print(error)
    print(f'{Fore.RED}{"#" * 30}{Style.RESET_ALL}')


def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_open(ws):
    print("Opened connection")
    ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands")
    ws.send("PASS SCHMOOPIIE")
    ws.send("NICK justinfan1")
    ws.send("USER justinfan1 * :justinfan1")
    for channel in channels:
        ws.send(f"JOIN #{channel}")


def handle_exit(signal, frame):
    print(f'{Fore.BLUE}{"#" * 30}')
    print(f"{Fore.GREEN}Interrupt signal received: Saving messages to the database...")
    if bot.conn:
        bot.db_commit()
        bot.conn.close()
        print(f"{Fore.GREEN}Database connection closed.")
    print(f'{Fore.BLUE}{"#" * 30}{Style.RESET_ALL}')

    sys.exit(1)


if __name__ == "__main__":
    bot = Bot()

    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        "wss://irc-ws.chat.twitch.tv/",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    ws.run_forever(dispatcher=rel, reconnect=2)

    rel.signal(2, rel.abort)  # Keyboard Interrupt
    signal.signal(signal.SIGINT, handle_exit)  # Keyboard Interrupt

    rel.dispatch()
