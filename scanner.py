import os
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

# Uniswap contract addresses on Base
UNISWAP_V2_ROUTER = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"
UNISWAP_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"
UNISWAP_UNIVERSAL_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"
UNISWAP_V4_POOL_MANAGER = "0xC2aB7dD270D16e6C64Dc33fb99eD888aEdE5e623"
UNISWAP_V2_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6"

# Minimal ABI for V2 pair contract
PAIR_ABI = [
    {"constant": True, "inputs": [], "name": "getReserves", "outputs": [
        {"name": "_reserve0", "type": "uint112"},
        {"name": "_reserve1", "type": "uint112"},
        {"name": "_blockTimestampLast", "type": "uint32"}
    ], "type": "function"},
    {"constant": True, "inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "type": "function"}
]

def send_telegram_message(message):
    try:
        print(f"Sending Telegram message: {message[:50]}...")
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
            return response.get("result")
        else:
            print(f"Basescan API error: {response.get('message')}")
            return None
    except Exception as e:
        print(f"Error fetching token info: {e}")
        return None

def has_liquidity(token_address, block_number=None):
    factory = w3.eth.contract(address=UNISWAP_V2_FACTORY, abi=[
        {"constant": True, "inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}], 
         "name": "getPair", "outputs": [{"name": "", "type": "address"}], "type": "function"}
    ])
    WETH = "0x4200000000000000000000000000000000000006"
    pair_address = factory.functions.getPair(token_address, WETH).call()
    
    if pair_address == "0x0000000000000000000000000000000000000000":
        print(f"No V2 liquidity pair found for {token_address} at block {block_number}")
        return False
    
    pair_contract = w3.eth.contract(address=pair_address, abi=PAIR_ABI)
    try:
        reserves = pair_contract.functions.getReserves().call(block_identifier=block_number)
        token0 = pair_contract.functions.token0().call()
        reserve = reserves[0] if token0 == token_address else reserves[1]
        has_liq = reserve > 0
        print(f"Token {token_address} has V2 liquidity at block {block_number}: {has_liq} (reserve: {reserve})")
        return has_liq
    except Exception as e:
        print(f"Error checking V2 liquidity for {token_address} at block {block_number}: {e}")
        return False

def process_block(block_number):
    print(f"Fetching block {block_number}")
    try:
        block = w3.eth.get_block(block_number, full_transactions=True)
        print(f"Block {block_number} fetched, processing {len(block.transactions)} transactions")
    except Exception as e:
        print(f"Error fetching block {block_number}: {e}")
        return False

    for tx in block.transactions:
        if tx.to and tx.input.hex().startswith("0x095ea7b3"):
            token_address = tx.to
            spender = "0x" + tx.input[34:74]
            try:
                amount = int(tx.input[74:], 16)
                print(f"Approval detected in tx {tx.hash.hex()}: {amount} approved to {spender}")
            except Exception as ex:
                print(f"Error parsing amount for tx {tx.hash.hex()}: {ex}")
                continue

            uniswap_spenders = [
                UNISWAP_V2_ROUTER.lower(),
                UNISWAP_V3_ROUTER.lower(),
                UNISWAP_UNIVERSAL_ROUTER.lower(),
                UNISWAP_V4_POOL_MANAGER.lower()
            ]
            if spender.lower() not in uniswap_spenders:
                print(f"Spender {spender} is not a Uniswap contract, skipping")
                continue

            if has_liquidity(token_address, block_number):
                print(f"Token {token_address} already has V2 liquidity at block {block_number}, skipping")
                continue

            token_info = get_token_info(token_address)
            if token_info:
                spender_version = {
                    UNISWAP_V2_ROUTER.lower(): "V2 Router",
                    UNISWAP_V3_ROUTER.lower(): "V3 Router",
                    UNISWAP_UNIVERSAL_ROUTER.lower(): "Universal Router",
                    UNISWAP_V4_POOL_MANAGER.lower(): "V4 PoolManager"
                }.get(spender.lower(), "Unknown")
                message = f"🚨 **Pre-Liquidity Uniswap Approval Detected** 🚨\n\n"
                message += f"**Tx Hash:** [ {tx.hash.hex()} ](https://basescan.org/tx/{tx.hash.hex()})\n"
                message += f"**Token:** {token_info.get('name', 'Unknown')} ({token_info.get('symbol', 'Unknown')})\n"
                message += f"**Contract:** [ {token_address} ](https://basescan.org/address/{token_address})\n"
                message += f"**Approved By:** [ {tx['from']} ](https://basescan.org/address/{tx['from']})\n"
                message += f"**Approved To:** [ {spender} ](https://basescan.org/address/{spender}) ({spender_version})\n"
                message += f"**Amount:** {amount}\n"
                message += f"**Note:** No liquidity detected on Uniswap V2 at block {block_number}"
                send_telegram_message(message)
            else:
                print(f"No token info for {token_address}, skipping alert")
    return True

def scan_approvals(start_block=None):
    print("Checking Web3 connection...")
    if not w3.is_connected():
        print("Web3 connection failed!")
        return
    print("Web3 connected successfully")

    last_processed = start_block if start_block is not None else w3.eth.block_number
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
    print("Environment variables loaded:")
    print(f"ALCHEMY_RPC: {ALCHEMY_RPC}")
    print(f"BASESCAN_API_KEY: {BASESCAN_API[:5]}...")
    print(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}...")
    print(f"TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

    send_telegram_message("🔍 Uniswap Pre-Liquidity Scanner Bot Started (V2, V3, V4, Universal)")
    print("Bot initialized, starting scan from block 13975865 for testing...")
    scan_approvals(start_block=13975865)  # Start at your test block
