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

UNISWAP_V2_ROUTER = Web3.to_checksum_address("0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24")
UNISWAP_V3_ROUTER = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
UNISWAP_V4_POOL_MANAGER = Web3.to_checksum_address("0xC2aB7dD270D16e6C64Dc33fb99eD888aEdE5e623")
UNISWAP_UNIVERSAL_ROUTER = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

UNISWAP_ROUTERS = {
    UNISWAP_V2_ROUTER: "Uniswap V2 Router",
    UNISWAP_V3_ROUTER: "Uniswap V3 Router",
    UNISWAP_V4_POOL_MANAGER: "Uniswap V4 Pool Manager",
    UNISWAP_UNIVERSAL_ROUTER: "Uniswap Universal Router"
}

SNIPER_BOT_ADDRESSES = [
    Web3.to_checksum_address("0x1234567890abcdef1234567890abcdef12345678"),
    Web3.to_checksum_address("0xabcdef1234567890abcdef1234567890abcdef12"),
    # Add real sniper bot addresses here
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

        if spender in UNISWAP_ROUTERS:
            process_approval(from_address, token_address, spender, amount, tx['hash'].hex(), block_number)
        else:
            print(f"Spender {spender} not in UNISWAP_ROUTERS, skipping")
    except Exception as e:
        print(f"Error processing tx {tx['hash'].hex()}: {e}")

def process_approval(from_address, token_address, spender, amount, tx_hash, block_number):
    is_sniper_bot = from_address in SNIPER_BOT_ADDRESSES
    sniper_note = "⚠️ *Known Sniper Bot Detected* ⚠️" if is_sniper_bot else ""
    name, symbol = get_token_details(token_address)
    router_name = UNISWAP_ROUTERS[spender]

    message = (
        f"🚨 *New Token Approval Detected* 🚨\n\n"
        f"*Tx Hash:* [{tx_hash}](https://basescan.org/tx/{tx_hash})\n"
        f"*Token:* {name} ({symbol})\n"
        f"*Contract:* [{token_address}](https://basescan.org/address/{token_address})\n"
        f"*Approved By:* [{from_address}](https://basescan.org/address/{from_address})\n"
        f"*Approved To:* [{spender}](https://basescan.org/address/{spender}) ({router_name})\n"
        f"*Amount:* {amount / 10**18:.2f} tokens\n"
        f"*Block:* {block_number}\n"
        f"{sniper_note}"
    )
    send_telegram_message(message)
    print(f"Approval detected for {token_address} to {router_name} in block {block_number}{' by sniper bot' if is_sniper_bot else ''}")

def monitor_approvals():
    if not w3.is_connected():
        print("Failed to connect to Base network! Check ALCHEMY_BASE_RPC.")
        send_telegram_message("❌ Bot failed to connect to Base network!")
        return

    print("Connected to Base network. Starting approval monitoring 3 blocks behind...")
    send_telegram_message("✅ *Uniswap Pre-Liquidity Approval Monitor Started (V2, V3, V4, Universal)*")

    last_processed_block = w3.eth.block_number - 3  # Start 3 blocks behind

    while True:
        try:
            latest_block = w3.eth.block_number
            target_block = latest_block - 3  # Stay 3 blocks behind
            print(f"Latest block: {latest_block}, Target block: {target_block}, Last processed: {last_processed_block}")

            if target_block > last_processed_block:
                for block_num in range(last_processed_block + 1, target_block + 1):
                    try:
                        block = w3.eth.get_block(block_num, full_transactions=True)
                        print(f"Scanning block {block_num} (3 blocks behind {latest_block}) with {len(block['transactions'])} txs")
                        for tx in block['transactions']:
                            process_transaction(tx, block_num)
                    except Exception as e:
                        print(f"Error scanning block {block_num}: {e}")
                last_processed_block = target_block
            else:
                print(f"No new blocks to process yet, waiting... (target: {target_block})")

            time.sleep(1)  # Poll every second
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            send_telegram_message(f"⚠️ *Bot Error:* {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    print("Starting Uniswap Pre-Liquidity Approval Monitor...")
    print(f"RPC: {ALCHEMY_RPC[:20]}...")
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:5]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"Monitoring sniper bot addresses: {SNIPER_BOT_ADDRESSES}")
    monitor_approvals()
