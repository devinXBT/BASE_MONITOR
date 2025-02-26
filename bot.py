import os
import time
from dotenv import load_dotenv
from web3 import Web3
import telebot

# Load environment variables
load_dotenv()

# Set up environment variables
ALCHEMY_RPC = os.getenv("ALCHEMY_BASE_RPC")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Web3 and Telegram Bot
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Known Uniswap V2, V3, and Universal Router Addresses
UNISWAP_V2_ROUTER = Web3.to_checksum_address("0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24")
UNISWAP_V3_ROUTER = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
UNISWAP_UNIVERSAL_ROUTER = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# Define ERC-20 Approve method signature (0x095ea7b3)
APPROVE_METHOD_SIG = "0x095ea7b3"

# ERC-20 ABI for fetching token details (name, symbol)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]

# Helper function to send message to Telegram
def send_telegram_message(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode='Markdown')
        print(f"Sent Telegram message: {message[:50]}...")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# Helper function to get token details (name and symbol)
def get_token_details(token_address):
    try:
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        return name, symbol
    except Exception as e:
        print(f"Error fetching token details for {token_address}: {e}")
        return "Unknown", "Unknown"

# Helper function to process approval transactions
def process_transaction(tx, block_number):
    try:
        # Check for approval transactions (0x095ea7b3)
        if not tx.get('input') or not tx['input'].startswith(APPROVE_METHOD_SIG):
            print(f"Tx {tx['hash'].hex()} is not an approve call.")
            return

        # Extract relevant data from the transaction input
        input_data = tx['input'].hex()
        spender = Web3.to_checksum_address("0x" + input_data[34:74])  # Extract spender address
        token_address = Web3.to_checksum_address(tx['to'])  # Token address (approved token)
        amount = int(input_data[74:], 16)  # Amount approved
        from_address = Web3.to_checksum_address(tx['from'])  # From address (approver)

        print(f"Detected approve call: token={token_address}, spender={spender}, from={from_address}, amount={amount}")

        # Check if spender is one of the Uniswap routers
        if spender in [UNISWAP_V2_ROUTER, UNISWAP_V3_ROUTER, UNISWAP_UNIVERSAL_ROUTER]:
            name, symbol = get_token_details(token_address)
            message = (
                f"🚨 *New Token Approval Detected* 🚨\n\n"
                f"*Tx Hash:* [{tx['hash'].hex()}](https://basescan.org/tx/{tx['hash'].hex()})\n"
                f"*Token:* {name} ({symbol})\n"
                f"*Token Address:* [{token_address}](https://basescan.org/address/{token_address})\n"
                f"*Approved By:* [{from_address}](https://basescan.org/address/{from_address})\n"
                f"*Approved To:* [{spender}](https://basescan.org/address/{spender})\n"
                f"*Amount:* {amount / 10**18:.2f} tokens\n"
                f"*Block:* {block_number}\n"
            )
            send_telegram_message(message)
            print(f"Approval detected for token {token_address} to {spender} in block {block_number}")

    except Exception as e:
        print(f"Error processing tx {tx['hash'].hex()}: {e}")

# Monitor blockchain for transactions and process them
def monitor_transactions():
    if not w3.is_connected():
        print("Failed to connect to the Base network!")
        send_telegram_message("❌ Bot failed to connect to Base network!")
        return

    print("Connected to Base network. Monitoring transactions...")
    last_processed_block = w3.eth.block_number - 3  # Start 3 blocks behind for safety

    while True:
        try:
            latest_block = w3.eth.block_number
            target_block = latest_block - 3  # Stay 3 blocks behind
            print(f"Latest block: {latest_block}, Target block: {target_block}")

            if target_block > last_processed_block:
                # Process blocks from the last processed one up to the target block
                for block_num in range(last_processed_block + 1, target_block + 1):
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    print(f"Scanning block {block_num} with {len(block['transactions'])} transactions")
                    for tx in block['transactions']:
                        process_transaction(tx, block_num)

                last_processed_block = target_block  # Update last processed block
            else:
                print(f"No new blocks to process yet, waiting...")

            time.sleep(1)  # Poll every second

        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            send_telegram_message(f"⚠️ Bot Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    print("Starting the token approval monitor...")
    monitor_transactions()
