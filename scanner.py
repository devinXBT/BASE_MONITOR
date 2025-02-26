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

# Initialize Web3 and Telegram bot
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

APPROVE_METHOD_SIG = "0x095ea7b3"

def send_telegram_message(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode='Markdown')
        print(f"Sent Telegram message: {message[:50]}...")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_token_details(token_address):
    try:
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        return name, symbol
    except Exception as e:
        print(f"Error fetching token details for {token_address}: {e}")
        return "Unknown", "Unknown"

def process_transaction(tx, block_number):
    try:
        if not tx.get('to') or not tx.get('input'):
            print(f"Tx {tx['hash'].hex()} missing 'to' or 'input', skipping")
            return

        input_data = tx['input'].hex()
        if not input_data.startswith(APPROVE_METHOD_SIG):
            print(f"Tx {tx['hash'].hex()} not an approve call (method: {input_data[:10]})")
            return

        token_address = Web3.to_checksum_address(tx['to'])
        spender = Web3.to_checksum_address("0x" + input_data[34:74])
        amount = int(input_data[74:], 16)
        from_address = Web3.to_checksum_address(tx['from'])

        print(f"Detected approve call: token={token_address}, spender={spender}, from={from_address}, amount={amount}")
        report_approval(from_address, token_address, spender, amount, tx['hash'].hex(), block_number)
    except Exception as e:
        print(f"Error processing tx {tx['hash'].hex()}: {e}")

def report_approval(from_address, token_address, spender, amount, tx_hash, block_number):
    name, symbol = get_token_details(token_address)

    message = (
        f"🚨 *New Approve Transaction Detected* 🚨\n\n"
        f"*Tx Hash:* [{tx_hash}](https://basescan.org/tx/{tx_hash})\n"
        f"*Token:* {name} ({symbol})\n"
        f"*Contract:* [{token_address}](https://basescan.org/address/{token_address})\n"
        f"*Approved By:* [{from_address}](https://basescan.org/address/{from_address})\n"
        f"*Spender:* [{spender}](https://basescan.org/address/{spender})\n"
        f"*Amount:* {amount / 10**18:.2f} tokens\n"
        f"*Block:* {block_number}"
    )
    send_telegram_message(message)
    print(f"Reported approve tx for {token_address} in block {block_number}")

def monitor_approvals():
    if not w3.is_connected():
        print("Failed to connect to Base network! Check ALCHEMY_BASE_RPC.")
        send_telegram_message("❌ Bot failed to connect to Base network!")
        return

    print("Connected to Base network. Starting real-time approve transaction monitoring...")
    send_telegram_message("✅ *Approve Transaction Monitor Started*")

    last_processed_block = w3.eth.block_number  # Start at the latest block

    while True:
        try:
            latest_block = w3.eth.block_number
            print(f"Latest block: {latest_block}, Last processed: {last_processed_block}")
            if latest_block > last_processed_block:
                for block_num in range(last_processed_block + 1, latest_block + 1):
                    try:
                        block = w3.eth.get_block(block_num, full_transactions=True)
                        print(f"Scanning block {block_num} with {len(block['transactions'])} txs")
                        for tx in block['transactions']:
                            process_transaction(tx, block_num)
                    except Exception as e:
                        print(f"Error scanning block {block_num}: {e}")
                last_processed_block = latest_block
            else:
                print(f"No new blocks yet, waiting... (current: {latest_block})")

            time.sleep(1)  # Poll every second
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            send_telegram_message(f"⚠️ *Bot Error:* {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    print("Starting Approve Transaction Monitor...")
    print(f"RPC: {ALCHEMY_RPC[:20]}...")
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:5]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")
    monitor_approvals()
