import os
import json
import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

ALCHEMY_WS_URL = os.getenv("ALCHEMY_WS_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

web3 = Web3(Web3.WebsocketProvider(ALCHEMY_WS_URL))

ERC20_CREATION_EVENT = "0x60806040"  # Common ERC-20 contract creation bytecode prefix

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

def handle_new_transaction(tx):
    try:
        tx_receipt = web3.eth.get_transaction_receipt(tx["hash"])
        if not tx_receipt or not tx_receipt.contractAddress:
            return

        contract_address = tx_receipt.contractAddress.lower()
        bytecode = web3.eth.get_code(contract_address).hex()

        if bytecode.startswith(ERC20_CREATION_EVENT):
            message = f"🚀 New token contract detected!\n\n📍 Address: {contract_address}\n🔍 Explorer: https://basescan.org/address/{contract_address}"
            send_telegram_message(message)
            print(message)

    except Exception as e:
        print(f"Error processing transaction: {e}")

def monitor_new_blocks():
    print("🔍 Monitoring new token contracts on Base...")
    try:
        for block in web3.eth.filter("pending").get_new_entries():
            block_data = web3.eth.get_block(block, full_transactions=True)
            for tx in block_data.transactions:
                if tx.to is None:  # Only contract creation transactions
                    handle_new_transaction(tx)
    except Exception as e:
        print(f"Error in block monitoring: {e}")

if __name__ == "__main__":
    monitor_new_blocks()
