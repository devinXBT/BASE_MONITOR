import time
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from a .env file

ALCHEMY_RPC = os.getenv("ALCHEMY_BASE_RPC")
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))

while True:
    try:
        current_block = w3.eth.block_number
        print("Current block:", current_block)
    except Exception as e:
        print("Error:", e)
    time.sleep(5)
