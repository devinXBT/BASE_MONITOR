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
    bot.send_message(TELEGRAM_CHAT_ID, message)

def get_token_info(token_address):
    url = f"https://api.basescan.org/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={BASESCAN_API}"
    response = requests.get(url).json()
    if response.get("status") == "1":
        return response.get("result")
    return None

def process_block(block_number):
    try:
        block = w3.eth.get_block(block_number, full_transactions=True)
    except Exception as e:
        print(f"Error fetching block {block_number}: {e}")
        return False  # Indicate failure to process this block

    for tx in block.transactions:
        # Check if the transaction is an approval
        if tx.to and tx.input.hex().startswith("0x095ea7b3"):  # approve() signature
            token_address = tx.to
            spender = "0x" + tx.input[34:74]  # Extract spender address from input
            try:
                amount = int(tx.input[74:], 16)  # Extract approved amount
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
    return True  # Block processed successfully

def scan_approvals():
    # Start from the current block at startup
    last_processed = w3.eth.block_number
    print(f"Starting scanning from block: {last_processed}")
    
    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_processed:
                # Process each new block sequentially
                for block_number in range(last_processed + 1, current_block + 1):
                    success = process_block(block_number)
                    if success:
                        last_processed = block_number
                    else:
                        # If a block fails to fetch, wait before trying again
                        time.sleep(2)
                        break
            else:
                # No new block yet, wait a bit
                time.sleep(1)
        except Exception as e:
            print(f"General error in scan loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    send_telegram_message("🔍 Scanner Bot Started")
    scan_approvals()
