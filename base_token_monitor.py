import os
import requests
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv()

# Alchemy WebSocket URL
ALCHEMY_WS_URL = os.getenv("ALCHEMY_WS_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Web3 with WebSocket connection
web3 = Web3(Web3.LegacyWebSocketProvider(ALCHEMY_WS_URL))

# Function to send a Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

# Function to check for new token contracts
def monitor_new_contracts():
    print("🔍 Monitoring new token contracts on Base Network...")
    
   def monitor_new_blocks():
    print("🔍 Monitoring new blocks on Base Network...")
    
    latest_block = web3.eth.blockNumber  # Start with the current block number
    
    while True:
        try:
            # Get the latest block number
            new_block = web3.eth.blockNumber
            if new_block > latest_block:
                block_data = web3.eth.get_block(new_block, full_transactions=True)
                
                for tx in block_data['transactions']:
                    if tx['to'] is None:  # Contract creation transaction
                        receipt = web3.eth.get_transaction_receipt(tx['hash'])
                        if receipt and receipt.contractAddress:
                            contract_address = receipt.contractAddress.lower()
                            message = f"🚀 New Token Contract Detected!\n📍 Address: {contract_address}\n🔍 Explorer: https://basescan.org/address/{contract_address}"
                            send_telegram_message(message)
                            print(message)

                latest_block = new_block  # Update to the latest block number
        except Exception as e:
            print(f"Error: {e}")
    
    while True:
        try:
            new_transactions = subscription.get_new_entries()
            for tx_hash in new_transactions:
                tx = web3.eth.get_transaction(tx_hash)
                
                if tx and tx["to"] is None:  # Contract creation transaction
                    receipt = web3.eth.get_transaction_receipt(tx_hash)
                    
                    if receipt and receipt.contractAddress:
                        contract_address = receipt.contractAddress.lower()
                        message = f"🚀 New Token Contract Detected!\n📍 Address: {contract_address}\n🔍 Explorer: https://basescan.org/address/{contract_address}"
                        send_telegram_message(message)
                        print(message)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    monitor_new_contracts()
