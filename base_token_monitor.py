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
    
    subscription = web3.eth.filter("pending")  # Listen for pending transactions
    
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
