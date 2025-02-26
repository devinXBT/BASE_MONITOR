import os
from dotenv import load_dotenv
import telebot
from web3 import Web3
from eth_account import Account
import time
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

ALCHEMY_RPC = os.getenv("ALCHEMY_BASE_RPC")  # e.g., https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logger.info(f"Loaded ALCHEMY_RPC: {ALCHEMY_RPC[:20]}...")
logger.info(f"Loaded TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:5]}...")
logger.info(f"Loaded TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

# Check environment variables
if not all([ALCHEMY_RPC, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    logger.error("Missing required environment variables!")
    exit(1)

# Initialize Web3
try:
    w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))
    if w3.is_connected():
        logger.info("Successfully connected to Base network!")
    else:
        logger.error("Failed to connect to Base network!")
        exit(1)
except Exception as e:
    logger.error(f"Web3 initialization error: {e}")
    exit(1)

# Initialize Telegram bot
try:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    logger.info("Telegram bot initialized successfully!")
except Exception as e:
    logger.error(f"Telegram bot initialization error: {e}")
    exit(1)

# Uniswap V2 contracts on Base
UNISWAP_V2_FACTORY = Web3.to_checksum_address("0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6")
UNISWAP_V2_ROUTER = Web3.to_checksum_address("0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24")
WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")

# ABIs (unchanged from previous)
UNISWAP_V2_ROUTER_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

UNISWAP_V2_FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "token0", "type": "address"},
            {"indexed": True, "name": "token1", "type": "address"},
            {"indexed": False, "name": "pair", "type": "address"},
            {"indexed": False, "name": "length", "type": "uint256"}
        ],
        "name": "PairCreated",
        "type": "event"
    }
]

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# User wallets and sniping settings
user_wallets = {}
user_snipe_settings = {}

def send_telegram_message(chat_id, message):
    try:
        bot.send_message(chat_id, message)
        logger.info(f"Sent message: {message[:50]}...")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    send_telegram_message(chat_id, "Welcome to Sigma-like Bot!\nCommands:\n/newwallet - Create a new wallet\n/importwallet - Import a wallet\n/exportwallet - Export your wallet\n/buy - Buy tokens\n/sell - Sell tokens\n/snipe - Start auto-sniping (e.g., /snipe 0.1)")

@bot.message_handler(commands=['newwallet'])
def handle_new_wallet(message):
    chat_id = message.chat.id
    account = Account.create()
    user_wallets[chat_id] = {'address': account.address, 'private_key': account.key.hex()}
    send_telegram_message(chat_id, f"New wallet created!\nAddress: {account.address}\nPrivate Key: {account.key.hex()}\nSave this securely!")

@bot.message_handler(commands=['importwallet'])
def handle_import_wallet(message):
    chat_id = message.chat.id
    send_telegram_message(chat_id, "Please send your private key (e.g., 0xabc...).")
    bot.register_next_step_handler(message, process_import_wallet)

def process_import_wallet(message):
    chat_id = message.chat.id
    private_key = message.text.strip()
    try:
        account = Account.from_key(private_key)
        user_wallets[chat_id] = {'address': account.address, 'private_key': private_key}
        send_telegram_message(chat_id, f"Wallet imported!\nAddress: {account.address}")
    except Exception as e:
        send_telegram_message(chat_id, f"Error importing wallet: {str(e)}")

@bot.message_handler(commands=['exportwallet'])
def handle_export_wallet(message):
    chat_id = message.chat.id
    if chat_id in user_wallets:
        wallet = user_wallets[chat_id]
        send_telegram_message(chat_id, f"Your wallet:\nAddress: {wallet['address']}\nPrivate Key: {wallet['private_key']}")
    else:
        send_telegram_message(chat_id, "No wallet found. Use /newwallet or /importwallet first.")

@bot.message_handler(commands=['buy'])
def handle_buy(message):
    chat_id = message.chat.id
    if chat_id not in user_wallets:
        send_telegram_message(chat_id, "No wallet found. Use /newwallet or /importwallet first.")
        return
    send_telegram_message(chat_id, "Enter token address and ETH amount (e.g., 0xTokenAddress 0.1)")
    bot.register_next_step_handler(message, process_buy)

def process_buy(message):
    chat_id = message.chat.id
    wallet = user_wallets[chat_id]
    try:
        token_address, eth_amount = message.text.split()
        eth_amount_wei = int(float(eth_amount) * 10**18)

        router = w3.eth.contract(address=UNISWAP_V2_ROUTER, abi=UNISWAP_V2_ROUTER_ABI)
        tx = router.functions.swapExactETHForTokens(
            0,
            [WETH, Web3.to_checksum_address(token_address)],
            wallet['address'],
            int(time.time()) + 60
        ).build_transaction({
            'from': wallet['address'],
            'value': eth_amount_wei,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet['address']),
            'chainId': 8453
        })

        signed_tx = w3.eth.account.sign_transaction(tx, wallet['private_key'])
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        send_telegram_message(chat_id, f"Buy tx sent! Hash: {tx_hash.hex()}")
    except Exception as e:
        send_telegram_message(chat_id, f"Error buying token: {str(e)}")

@bot.message_handler(commands=['sell'])
def handle_sell(message):
    chat_id = message.chat.id
    if chat_id not in user_wallets:
        send_telegram_message(chat_id, "No wallet found. Use /newwallet or /importwallet first.")
        return
    send_telegram_message(chat_id, "Enter token address and amount (e.g., 0xTokenAddress 100)")
    bot.register_next_step_handler(message, process_sell)

def process_sell(message):
    chat_id = message.chat.id
    wallet = user_wallets[chat_id]
    try:
        token_address, amount = message.text.split()
        amount_wei = int(float(amount) * 10**18)

        token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        approve_tx = token_contract.functions.approve(UNISWAP_V2_ROUTER, amount_wei).build_transaction({
            'from': wallet['address'],
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet['address']),
            'chainId': 8453
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, wallet['private_key'])
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
        print(f"Approve tx sent: {approve_tx_hash.hex()}")
        time.sleep(10)

        router = w3.eth.contract(address=UNISWAP_V2_ROUTER, abi=UNISWAP_V2_ROUTER_ABI)
        tx = router.functions.swapExactTokensForETH(
            amount_wei,
            0,
            [Web3.to_checksum_address(token_address), WETH],
            wallet['address'],
            int(time.time()) + 60
        ).build_transaction({
            'from': wallet['address'],
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet['address']),
            'chainId': 8453
        })

        signed_tx = w3.eth.account.sign_transaction(tx, wallet['private_key'])
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        send_telegram_message(chat_id, f"Sell tx sent! Hash: {tx_hash.hex()}")
    except Exception as e:
        send_telegram_message(chat_id, f"Error selling token: {str(e)}")

@bot.message_handler(commands=['snipe'])
def handle_snipe(message):
    chat_id = message.chat.id
    if chat_id not in user_wallets:
        send_telegram_message(chat_id, "No wallet found. Use /newwallet or /importwallet first.")
        return
    try:
        eth_amount = float(message.text.split()[1])  # e.g., /snipe 0.1
        eth_amount_wei = int(eth_amount * 10**18)
        user_snipe_settings[chat_id] = {'eth_amount': eth_amount_wei, 'active': True}
        send_telegram_message(chat_id, f"Sniping started with {eth_amount} ETH!")
        monitor_new_pairs(chat_id)
    except Exception as e:
        send_telegram_message(chat_id, "Usage: /snipe <ETH amount> (e.g., /snipe 0.1)")

def monitor_new_pairs(chat_id):
    factory = w3.eth.contract(address=UNISWAP_V2_FACTORY, abi=UNISWAP_V2_FACTORY_ABI)
    last_processed_block = w3.eth.block_number
    logger.info(f"Starting sniping at block: {last_processed_block}")

    while user_snipe_settings.get(chat_id, {}).get('active', False):
        try:
            latest_block = w3.eth.block_number
            if latest_block > last_processed_block:
                events = factory.events.PairCreated.get_logs(fromBlock=last_processed_block + 1, toBlock=latest_block)
                for event in events:
                    token0 = event['args']['token0']
                    token1 = event['args']['token1']
                    pair = event['args']['pair']
                    logger.info(f"New pair detected: {token0} - {token1}, Pair: {pair}")
                    
                    token_to_buy = token1 if token0 == WETH else token0
                    snipe_token(chat_id, token_to_buy)
                
                last_processed_block = latest_block
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in sniping loop: {e}")
            send_telegram_message(chat_id, f"Snipe Error: {str(e)}")
            time.sleep(5)

def snipe_token(chat_id, token_address):
    wallet = user_wallets[chat_id]
    eth_amount_wei = user_snipe_settings[chat_id]['eth_amount']

    try:
        router = w3.eth.contract(address=UNISWAP_V2_ROUTER, abi=UNISWAP_V2_ROUTER_ABI)
        tx = router.functions.swapExactETHForTokens(
            0,
            [WETH, Web3.to_checksum_address(token_address)],
            wallet['address'],
            int(time.time()) + 60
        ).build_transaction({
            'from': wallet['address'],
            'value': eth_amount_wei,
            'gas': 250000,
            'gasPrice': w3.eth.gas_price * 2,
            'nonce': w3.eth.get_transaction_count(wallet['address']),
            'chainId': 8453
        })

        signed_tx = w3.eth.account.sign_transaction(tx, wallet['private_key'])
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        send_telegram_message(chat_id, f"Sniped token {token_address}! Hash: {tx_hash.hex()}")
    except Exception as e:
        send_telegram_message(chat_id, f"Error sniping token {token_address}: {str(e)}")

# Start bot polling
if __name__ == "__main__":
    logger.info("Starting Sigma-like Bot...")
    bot.polling(none_stop=True)
