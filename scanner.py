
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

def send_telegram_message(message):
    try:
        print(f"Sending Telegram message: {message[:50]}...")  # Debug
        bot.send_message(TELEGRAM_CHAT_ID, message)
        print("Telegram message sent successfully")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_token_info(token_address):
    print(f"Fetching token info for {token_address}")
    url = f"https://api.basescan.org/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={BASESCAN_API}"
    try:
        response = requests.get(url).json()
        if response.get("status") == "1":
            print(f"Token info retrieved: {response.get('result')}")
            return response.get("result")
        else:
            print(f"Basescan API error: {response.get('message')}")
            return None
    except Exception as e:
        print(f"Error fetching token info: {e}")
        return None

def process_block(block_number):
    print(f"Fetching block {block_number}")
    try:
        block = w3.eth.get_block(block_number, full_transactions=True)
        print(f"Block {block_number} fetched, processing {len(block.transactions)} transactions")
    except Exception as e:
        print(f"Error fetching block {block_number}: {e}")
        return False

    for tx in block.transactions:
        if tx.to and tx.input.hex().startswith("0x095ea7b3"):  # approve() signature
            token_address = tx.to
            spender = "0x" + tx.input[34:74]
            try:
                amount = int(tx.input[74:], 16)
                print(f"Approval detected in tx {tx.hash.hex()}: {amount} approved")
            except Exception as ex:
                print(f"Error parsing amount for tx {tx.hash.hex()}: {ex}")
                continue

            token_info = get_token_info(token_address)
            if token_info:
                message = f"🚨 **Token Approval Detected** 🚨\n\n"
                message += f"**Token:** {token_info.get('name')} ({token_info.get('symbol')})\n"
                message += f"**Contract:** [ {token_address} ](https://basescan.org/address/{token_address})\n"
                message += f"**Approved By:** [ {tx['from']} ](https://basescan.org/address/{tx['from']})\n"
                message += f"**Approved To:** [ {spender} ](https://basescan.org/address/{spender})\n"
                message += f"**Amount:** {amount}\n"
                send_telegram_message(message)
    return True

def scan_approvals():
    print("Checking Web3 connection...")
    if not w3.is_connected():
        print("Web3 connection failed!")
        return
    print("Web3 connected successfully")

    last_processed = w3.eth.block_number
    print(f"Starting scanning from block: {last_processed}")
    
    while True:
        try:
            print("Fetching current block number...")
            current_block = w3.eth.block_number
            print(f"Current block: {current_block}, Last processed: {last_processed}")
            if current_block > last_processed:
                for block_number in range(last_processed + 1, current_block + 1):
                    print(f"Processing block {block_number}...")
                    success = process_block(block_number)
                    if success:
                        last_processed = block_number
                        print(f"Successfully processed block {last_processed}")
                    else:
                        print(f"Failed to process block {block_number}, retrying after delay")
                        time.sleep(2)
                        break
            else:
                print("No new blocks yet, waiting...")
                time.sleep(1)
        except Exception as e:
            print(f"General error in scan loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    # Verify environment variables
    print("Environment variables loaded:")
    print(f"ALCHEMY_RPC: {ALCHEMY_RPC}")
    print(f"BASESCAN_API_KEY: {BASESCAN_API[:5]}...")  # Partial for security
    print(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}...")
    print(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

    send_telegram_message("🔍 Scanner Bot Started")
    print("Bot initialized, starting scan...")
    scan_approvals()
