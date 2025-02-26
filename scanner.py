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

w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

UNISWAP_V2_FACTORY = Web3.to_checksum_address("0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6")
UNISWAP_V2_ROUTER = Web3.to_checksum_address("0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24")
UNISWAP_V3_ROUTER = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
UNISWAP_V4_POOL_MANAGER = Web3.to_checksum_address("0xC2aB7dD270D16e6C64Dc33fb99eD888aEdE5e623")
UNISWAP_UNIVERSAL_ROUTER = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

PAIR_ABI = [
    {"constant": True, "inputs": [], "name": "getReserves", "outputs": [
        {"name": "_reserve0", "type": "uint112"},
        {"name": "_reserve1", "type": "uint112"},
        {"name": "_blockTimestampLast", "type": "uint32"}
    ], "type": "function"},
    {"constant": True, "inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "type": "function"}
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

APPROVAL_EVENT_SIG = "0x8c5be1e5ea6b5a2e4b167f05063e32c8e8c9b0c951938c0e93e316b58312b805"

def send_telegram_message(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode='Markdown')
        print(f"Sent Telegram message: {message[:50]}...")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_pair_address(token_address):
    factory = w3.eth.contract(address=UNISWAP_V2_FACTORY, abi=[
        {"constant": True, "inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}],
         "name": "getPair", "outputs": [{"name": "", "type": "address"}], "type": "function"}
    ])
    return factory.functions.getPair(token_address, WETH).call()

def has_liquidity(token_address):
    pair_address = get_pair_address(token_address)
    if pair_address == "0x0000000000000000000000000000000000000000":
        return False
    pair_contract = w3.eth.contract(address=pair_address, abi=PAIR_ABI)
    try:
        reserves = pair_contract.functions.getReserves().call()
        token0 = pair_contract.functions.token0().call()
        reserve = reserves[0] if token0 == token_address else reserves[1]
        return reserve > 0
    except Exception:
        return False

def get_token_details(token_address):
    try:
        contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        return name, symbol
    except Exception as e:
        print(f"Error fetching token details: {e}")
        return "Unknown", "Unknown"

def process_transaction(tx, block_number):
    # Direct approve calls
    if tx.get('to') and tx.get('input'):
        input_data = tx['input'].hex()
        if input_data.startswith("0x095ea7b3"):
            token_address = Web3.to_checksum_address(tx['to'])
            spender = Web3.to_checksum_address("0x" + input_data[34:74])
            amount = int(input_data[74:], 16)
            from_address = Web3.to_checksum_address(tx['from'])
            if spender in UNISWAP_ROUTERS:
                process_approval(from_address, token_address, spender, amount, tx['hash'].hex(), block_number)

    # Approval events in logs
    try:
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        for log in receipt['logs']:
            if len(log['topics']) > 0 and log['topics'][0].hex() == APPROVAL_EVENT_SIG:
                token_address = Web3.to_checksum_address(log['address'])
                from_address = Web3.to_checksum_address("0x" + log['topics'][1].hex()[26:])
                spender = Web3.to_checksum_address("0x" + log['topics'][2]?.hex()[26:])
                amount = int(log['data'], 16)
                if spender in UNISWAP_ROUTERS:
                    process_approval(from_address, token_address, spender, amount, tx['hash'].hex(), block_number)
    except Exception as e:
        print(f"Error fetching receipt for tx {tx['hash'].hex()}: {e}")

def process_approval(from_address, token_address, spender, amount, tx_hash, block_number):
    if has_liquidity(token_address):
        print(f"Tx {tx_hash}: Token {token_address} has liquidity, skipping")
        return

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
        f"*Status:* No liquidity on Uniswap V2 yet\n"
        f"*Block:* {block_number}\n"
        f"{sniper_note}"
    )
    send_telegram_message(message)
    print(f"Approval detected for {token_address} to {router_name} in block {block_number}{' by sniper bot' if is_sniper_bot else ''}")

def monitor_approvals():
    if not w3.is_connected():
        print("Failed to connect to Base network!")
        send_telegram_message("❌ Bot failed to connect to Base network!")
        return

    print("Connected to Base network. Starting approval monitoring 20 blocks behind...")
    send_telegram_message("✅ *Uniswap Pre-Liquidity Approval Monitor Started (V2, V3, V4, Universal)*")

    last_processed_block = w3.eth.block_number - 20  # Start 20 blocks behind

    while True:
        try:
            latest_block = w3.eth.block_number
            target_block = latest_block - 20  # Always stay 20 blocks behind

            if target_block > last_processed_block:
                for block_num in range(last_processed_block + 1, target_block + 1):
                    try:
                        block = w3.eth.get_block(block_num, full_transactions=True)
                        print(f"Scanning block {block_num} (20 blocks behind latest {latest_block}) with {len(block['transactions'])} txs")
                        for tx in block['transactions']:
                            process_transaction(tx, block_num)
                    except Exception as e:
                        print(f"Error scanning block {block_num}: {e}")
                last_processed_block = target_block

            time.sleep(1)  # Poll every second
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            send_telegram_message(f"⚠️ *Bot Error:* {str(e)}")
            time.sleep(5)  # Retry after delay

if __name__ == "__main__":
    print("Starting Uniswap Pre-Liquidity Approval Monitor...")
    print(f"RPC: {ALCHEMY_RPC[:20]}...")
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:5]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"Monitoring sniper bot addresses: {SNIPER_BOT_ADDRESSES}")
    monitor_approvals()
