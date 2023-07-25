import sqlite3
from twitchio.ext import commands
import time
import colorama
from colorama import Fore, Style
import random
import signal
import sys
import re

channels = ["1channel", "2channel", "3channel"]
token = "bot_token" 
client_id = "bot_client_id"
nick = "bot_nick"
save_interval = 60  # Save messages every 60 seconds
msg_per_sec_updater = 2 # Update msg/s every 2 seconds

conn = sqlite3.connect('chatlog.db')
c = conn.cursor()

# Create tables for each channel
for channel in channels:
    c.execute(f'''CREATE TABLE IF NOT EXISTS {channel}
                 (timestamp TEXT, username TEXT, message TEXT)''')

conn.commit()

colorama.init()  # Initialize colorama

class Bot(commands.Bot):
    async def event_ready(self):
        print(f'Logged in as {self.nick}')

    def __init__(self):
        super().__init__(token=token, client_id=client_id, nick=nick, prefix='',
                         initial_channels=channels)
        
        # ------------------------------
        self.msg_per_sec = 0
        self.channel_message_count = 0
        self.channel_colors = self.assign_colors_to_channels()
        self.last_save_time = time.time()
        self.max_msg_per_sec = 0 
        self.word_count = 0
        self.word_start_time = time.time()
        self.msg_per_sec = 0
        self.last_avg = time.time()

    def assign_colors_to_channels(self):
        # Shuffle the available colors and assign them to channels
        available_colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.LIGHTGREEN_EX, Fore.LIGHTBLUE_EX]
        random.shuffle(available_colors)
        channel_colors = {}

        for i, channel in enumerate(channels):
            channel_colors[channel] = available_colors[i % len(available_colors)]

        return channel_colors


    def calculate_gradient_color(self, count_per_sec):
        # Calculate the upper limit for the gradient based on the maximum count per second observed
        gradient_upper_limit = max(self.max_msg_per_sec, 1)  # Avoid division by zero

        # Calculate the normalized value for the current count_per_sec within the gradient range
        normalized_value = min(count_per_sec, gradient_upper_limit) / gradient_upper_limit

        # Calculate the RGB values for the gradient color
        r = int((1 - normalized_value) * 255)
        g = int(normalized_value * 255)
        b = 0

        # Generate the ANSI escape sequence for the gradient color
        ansi_color = 16 + (36 * int(r / 255 * 5)) + (6 * int(g / 255 * 5)) + int(b / 255 * 5)

        # Return the ANSI color escape sequence
        return f"\x1b[38;5;{ansi_color}m"

    async def event_message(self, message):
        # Extract channel from the message
        channel = message.channel.name

        # Log chat messages to the database with timestamp
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        c.execute("INSERT INTO {} VALUES (?, ?, ?)".format(channel), (timestamp, message.author.name, message.content))
        
        

        # Increment message count
        self.channel_message_count += 1


        # Calculate messages per second (msg/s)
        elapsed_time_msg = time.time() - self.last_avg
        if elapsed_time_msg >= msg_per_sec_updater:
            self.msg_per_sec = self.channel_message_count / elapsed_time_msg
            self.channel_message_count = 0
            self.last_avg = time.time()

        # Update the maximum messages per second observed across all channels
        self.max_msg_per_sec = max(self.max_msg_per_sec, self.msg_per_sec)

        # Calculate words per second (words/s) for the channel
        self.word_count += len(re.findall(r'\b\w+\b', message.content))
        elapsed_time_word = time.time() - self.word_start_time
        words_per_sec = self.word_count / elapsed_time_word

        enc_message = message.content

        # Get the color for the channel
        color = self.channel_colors[channel]

        # Calculate the gradient color for the messages per second
        gradient_color_msg = self.calculate_gradient_color(self.msg_per_sec)

        # Calculate the gradient color for the words per second
        gradient_color_word = self.calculate_gradient_color(words_per_sec)

        # Print chat messages to the terminal with color
        print(f'{timestamp} {gradient_color_msg}({self.msg_per_sec:.2f} msg/s) {gradient_color_word}({words_per_sec:.2f} words/s) {color}[{channel}] {message.author.name}: {enc_message}{Style.RESET_ALL}')

        await self.handle_commands(message)

        # Check if it's time to save the messages to the database
        current_time = time.time()
        if current_time - self.last_save_time >= save_interval:
            print(f'{Fore.YELLOW}{"#" * 30}')
            print(f'{Fore.YELLOW}{"DB updates..."}')
            print(f'{Fore.YELLOW}{"#" * 30}{Style.RESET_ALL}')
            conn.commit()  # Commit changes to the database
            self.last_save_time = current_time

    

bot = Bot()

def handle_exit(signal, frame):
    print("\nInterrupt signal received: Saving messages to the database...")
    conn.commit()  # Commit any pending changes to the database
    conn.close()  # Close the database connection
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

bot.run()
