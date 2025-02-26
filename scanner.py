import os
import json
import requests
import telebot
from web3 import Web3
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

ALCHEMY_RPC = os.getenv("ALCHEMY_BASE_RPC")
BASESCAN_API = os.getenv("BASESCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Web3 and Telegram bot
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Function to send Telegram alerts
def send_telegram_message(message):
    bot.send_message(TELEGRAM_CHAT_ID, message)

# Function to get token details from BaseScan
def get_token_info(token_address):
    url = f"https://api.basescan.org/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={BASESCAN_API}"
    response = requests.get(url).json()
    if response["status"] == "1":
        return response["result"]
    return None

# Function to scan for new token approvals
def scan_approvals():
    latest_block = w3.eth.block_number
    while True:
        try:
            # Check if the block exists before trying to fetch it
            if w3.eth.get_block(latest_block) is not None:
                block = w3.eth.get_block(latest_block, full_transactions=True)

                for tx in block.transactions:
                    if tx.to and tx.input.hex().startswith("0x095ea7b3"):  # `approve()` function signature
                        token_address = tx.to
                        spender = "0x" + tx.input[34:74]  # Extract spender address
                        amount = int(tx.input[74:], 16)  # Extract approved amount
                        
                        token_info = get_token_info(token_address)
                        if token_info:
                            message = f"🚨 **Token Approval Detected** 🚨\n\n"
                            message += f"**Token:** {token_info['name']} ({token_info['symbol']})\n"
                            message += f"**Contract:** [{token_address}](https://basescan.org/address/{token_address})\n"
                            message += f"**Approved By:** [{tx['from']}](https://basescan.org/address/{tx['from']})\n"
                            message += f"**Approved To:** [{spender}](https://basescan.org/address/{spender})\n"
                            message += f"**Amount:** {amount}\n"
                            send_telegram_message(message)

            # Increment to check the next block
            latest_block += 1

        except Exception as e:
            print(f"Error: {e}")
            # If there’s an error fetching the block, wait and retry
            latest_block += 1
            time.sleep(1)  # Optional: Add a delay before retrying

# Start scanning
if __name__ == "__main__":
    send_telegram_message("🔍 Scanner Bot Started")
    scan_approvals()
