import time
from web3 import Web3
from telegram import Bot

# Telegram Bot setup
telegram_token = '7702711510:AAHwIAcx1z_Luv_-IjRaMWJq4UgTsekht2Y'  # Replace with your bot's token
telegram_chat_id = '6442285058'  # Replace with your chat ID
telegram_bot = Bot(token=telegram_token)

# Base network RPC URL (replace with actual RPC URL)
base_rpc_url = 'https://base-mainnet.g.alchemy.com/v2/vLkhOi55lDoMp6pu2OFcOSD7TCW5rjo7'
w3 = Web3(Web3.HTTPProvider(base_rpc_url))

# Uniswap V2 Factory contract address and method to get pairs (example address)
uniswap_v2_factory_address = '0x5C69bEe701ef814a2B6a3EDD4B52bC2cD7B5b6C2'  # Uniswap V2 Factory address
uniswap_v2_abi = '''[...]'''  # ABI for Uniswap V2 Factory (you need to add the full ABI here)

# Uniswap V3 Factory contract address (example address)
uniswap_v3_factory_address = '0x1F98431c8aD98523631AE4a59f2677bC3e2A1e5'  # Uniswap V3 Factory address
uniswap_v3_abi = '''[...]'''  # ABI for Uniswap V3 Factory (you need to add the full ABI here)

# Signature for approve method (0x095ea7b3)
approve_signature = '0x095ea7b3'

# Define the function to send notifications to Telegram
def notify_telegram(message):
    telegram_bot.send_message(chat_id=telegram_chat_id, text=message)

# Define the function to check liquidity on Uniswap V2 and V3
def has_liquidity_on_uniswap(token_address):
    # Check liquidity on Uniswap V2
    uniswap_v2_factory = w3.eth.contract(address=uniswap_v2_factory_address, abi=uniswap_v2_abi)
    pair_address = uniswap_v2_factory.functions.getPair(token_address, w3.toChecksumAddress(uniswap_v2_factory_address)).call()

    if pair_address == '0x0000000000000000000000000000000000000000':
        return False  # No pair found on Uniswap V2
    
    # Check liquidity on Uniswap V3 (simplified for example purposes)
    uniswap_v3_factory = w3.eth.contract(address=uniswap_v3_factory_address, abi=uniswap_v3_abi)
    pool_address = uniswap_v3_factory.functions.getPool(token_address, w3.toChecksumAddress(uniswap_v3_factory_address), 3000).call()

    if pool_address == '0x0000000000000000000000000000000000000000':
        return False  # No pool found on Uniswap V3

    return True  # Liquidity exists on either Uniswap V2 or V3

# Define the function to handle approve transactions
def handle_approve_transaction(tx_hash):
    tx = w3.eth.get_transaction(tx_hash)
    
    # Check if the method is 'approve' (0x095ea7b3)
    if tx['input'].startswith(approve_signature):
        token_address = tx['to']
        spender = '0x' + tx['input'][34:74]
        amount = int(tx['input'][74:], 16)

        # Check if token has liquidity on Uniswap
        if not has_liquidity_on_uniswap(token_address):
            message = f"Token {token_address} approved for spending by {spender}. No liquidity on Uniswap yet!"
            notify_telegram(message)

# Define the function to monitor transactions
def monitor_transactions():
    while True:
        # Monitor new blocks for transactions
        latest_block = w3.eth.get_block('latest')  # Use get_block instead of getBlock

        for tx_hash in latest_block['transactions']:
            handle_approve_transaction(tx_hash)

        time.sleep(5)  # Delay to avoid spamming requests (adjust as needed)

if __name__ == '__main__':
    monitor_transactions()
