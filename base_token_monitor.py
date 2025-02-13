import os
import json
import asyncio
import websockets
from web3 import Web3
from web3.providers.websocket import LegacyWebSocketProvider
from telegram import Bot

# Environment variables
ALCHEMY_WS_URL = os.getenv("ALCHEMY_WS_URL", "wss://base-mainnet.g.alchemy.com/v2/qKYxGNNH-dvlcKwc4ckHo6I9Hqtp4CI8")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7702711510:AAHwIAcx1z_Luv_-IjRaMWJq4UgTsekht2Y")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6442285058")

# Initialize Telegram bot
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Web3 instance with LegacyWebSocketProvider
web3 = Web3(LegacyWebSocketProvider(ALCHEMY_WS_URL))

# ABI for ERC20 token contract (simplified)
ERC20_ABI = json.loads('''
[
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]
''')

async def monitor_new_tokens():
    """
    Monitors new token creation events on the Base network.
    """
    print("Connecting to Alchemy WebSocket...")
    async with websockets.connect(ALCHEMY_WS_URL) as ws:
        # Subscribe to new pending transactions
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newPendingTransactions"]
        }))

        # Listen for new transactions
        while True:
            response = await ws.recv()
            data = json.loads(response)

            if "params" in data:
                tx_hash = data["params"]["result"]
                print(f"New transaction detected: {tx_hash}")

                # Get transaction details
                tx = web3.eth.get_transaction(tx_hash)
                if tx.to is None:  # Contract creation transaction
                    print(f"New contract created: {tx_hash}")
                    await notify_new_token(tx_hash)

async def notify_new_token(tx_hash):
    """
    Sends a notification to Telegram about a new token.
    """
    # Get contract address (deployed contract)
    receipt = web3.eth.get_transaction_receipt(tx_hash)
    contract_address = receipt["contractAddress"]

    # Get token details
    token_contract = web3.eth.contract(address=contract_address, abi=ERC20_ABI)
    token_name = token_contract.functions.name().call()
    token_symbol = token_contract.functions.symbol().call()
    token_supply = token_contract.functions.totalSupply().call()

    # Send Telegram notification
    message = (
        f"🚨 New Token Created on Base Network 🚨\n\n"
        f"Contract Address: {contract_address}\n"
        f"Name: {token_name}\n"
        f"Symbol: {token_symbol}\n"
        f"Total Supply: {token_supply}\n"
        f"Transaction Hash: {tx_hash}"
    )
    await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    print(f"Notification sent for token: {token_name} ({token_symbol})")

if __name__ == "__main__":
    print("Starting Base Network Token Monitor...")
    asyncio.run(monitor_new_tokens())
