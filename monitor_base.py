import requests
from web3 import Web3
import os

# Load API keys from environment variables
ALCHEMY_WS_URL = os.getenv("ALCHEMY_WS_URL", "wss://base-mainnet.g.alchemy.com/v2/qKYxGNNH-dvlcKwc4ckHo6I9Hqtp4CI8")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7702711510:AAHwIAcx1z_Luv_-IjRaMWJq4UgTsekht2Y")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6442285058")

# Connect to Base network
try:
    web3 = Web3(Web3.WebsocketProvider(ALCHEMY_WS_URL))
except AttributeError:
    # Fallback to LegacyWebSocketProvider if WebsocketProvider is not available
    web3 = Web3(Web3.LegacyWebSocketProvider(ALCHEMY_WS_URL))

# Function to send Telegram alerts
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")

# Function to process new contract events
def handle_event(event):
    tx_hash = event["transactionHash"].hex()
    contract_address = event["address"]
    message = f"🚀 New Contract Deployed on Base!\n📍 Address: {contract_address}\n🔗 Tx: {tx_hash}"
    print(message)
    send_telegram_message(message)

# Subscribe to new contracts
def listen_for_contracts():
    print("Listening for new contract deployments on Base...")

    subscription = web3.eth.subscribe(
        'logs',
        {"topics": ["0x60806040"]}, # Contract creation topic
    )

    try:
        while True:
            event = web3.eth.get_filter_changes(subscription.filter_id)
            if event:
                handle_event(event[0])
    except KeyboardInterrupt:
        print("Stopped listening.")
        subscription.unsubscribe()

# Run the script
if __name__ == "__main__":
    if web3.is_Connected():
        listen_for_contracts()
    else:
        print("Failed to connect to Base network.")
