import os
from dotenv import load_dotenv
import telebot
from web3 import Web3
import time
from hexbytes import HexBytes

# Load environment variables
load_dotenv()

ALCHEMY_RPC = os.getenv("ALCHEMY_BASE_RPC")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"Loaded ALCHEMY_RPC: {ALCHEMY_RPC[:20]}...")
print(f"Loaded TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}...")
print(f"Loaded TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

# Initialize Web3 and Telegram bot
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

APPROVE_METHOD_SIG = "0x095ea7b3"

def send_telegram_message(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        print(f"Sent Telegram message: {message[:50]}...")
    except Exception as e:
        print(f"Telegram error: {e}")

def process_transaction(tx, block_number):
    try:
        if not tx.get('to') or not tx.get('input'):
            print(f"Tx {tx['hash'].hex()} missing 'to' or 'input', skipping")
            return

        input_data = tx['input'].hex()
        print(f"Processing tx {tx['hash'].hex()}, method: {input_data[:10]}")

        if input_data.startswith(APPROVE_METHOD_SIG):
            token_address = Web3.to_checksum_address(tx['to'])
            spender = Web3.to_checksum_address("0x" + input_data[34:74])
            amount = int(input_data[74:], 16)
            from_address = Web3.to_checksum_address(tx['from'])

            print(f"DETECTED APPROVE: token={token_address}, spender={spender}, from={from_address}, amount={amount}")
            report_approval(from_address, token_address, spender, amount, tx['hash'].hex(), block_number)
        else:
            print(f"Tx {tx['hash'].hex()} not an approve call")
    except Exception as e:
        print(f"Error processing tx {tx['hash'].hex()}: {e}")

def report_approval(from_address, token_address, spender, amount, tx_hash, block_number):
    message = (
        f"New Approve Tx Detected\n"
        f"Tx Hash: {tx_hash}\n"
        f"Token: {token_address}\n"
        f"From: {from_address}\n"
        f"Spender: {spender}\n"
        f"Amount: {amount / 10**18:.2f} tokens\n"
        f"Block: {block_number}"
    )
    send_telegram_message(message)
    print(f"Reported approve tx: {tx_hash}")

def monitor_approvals():
    if not w3.is_connected():
        print("Failed to connect to Base network! Check ALCHEMY_BASE_RPC.")
        send_telegram_message("Failed to connect to Base network!")
        return

    print("Successfully connected to Base network!")
    send_telegram_message("Approve Transaction Monitor Started")

    last_processed_block = w3.eth.block_number
    print(f"Starting at block: {last_processed_block}")

    while True:
        try:
            latest_block = w3.eth.block_number
            print(f"Latest block: {latest_block}, Last processed: {last_processed_block}")
            if latest_block > last_processed_block:
                for block_num in range(last_processed_block + 1, latest_block + 1):
                    print(f"Fetching block {block_num}...")
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    print(f"Scanning block {block_num} with {len(block['transactions'])} transactions")
                    for tx in block['transactions']:
                        process_transaction(tx, block_num)
                last_processed_block = latest_block
            else:
                print("No new blocks yet, waiting...")

            time.sleep(1)  # Poll every second
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            send_telegram_message(f"Bot Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    print("Starting Approve Transaction Monitor...")
    monitor_approvals()
