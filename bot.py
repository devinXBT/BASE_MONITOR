import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from web3 import Web3
import json

# Config
TELEGRAM_TOKEN = "7702711510:AAHwIAcx1z_Luv_-IjRaMWJq4UgTsekht2Y"  # From BotFather
WALLET_ADDRESS = "0xB00B2011a83403583129Aee95812EaE8E483D2aE"
PRIVATE_KEY = "0xe9df4273a5c7d7f4f3cd78e98495f61f446e368aca57d6fcb0e27fd5af9b3457"  # Keep this secure!
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/vLkhOi55lDoMp6pu2OFcOSD7TCW5rjo7"
ETHER_AMOUNT = "0.01"  # Amount to spend in ETH (adjustable)

# Web3 setup
w3 = Web3(Web3.HTTPProvider(BASE_RPC))
if not w3.is_connected():
    raise Exception("Cannot connect to Base network")

# Uniswap V2 Router on Base (example address, verify for Base)
UNISWAP_ROUTER_ADDRESS = "0x4752ba5DB52D97D632c2bEB16d6fAC7bC4bC9b9d"  # Replace with Base's router
with open("uniswap_router_abi.json", "r") as f:  # Get ABI from Uniswap docs or GitHub
    UNISWAP_ABI = json.load(f)
router = w3.eth.contract(address=UNISWAP_ROUTER_ADDRESS, abi=UNISWAP_ABI)

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /snipe <token_address> to buy a token on Base.")

async def snipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a token address: /snipe <token_address>")
        return
    
    token_address = context.args[0]
    if not w3.is_address(token_address):
        await update.message.reply_text("Invalid token address!")
        return

    try:
        # Build transaction
        amount_in = w3.to_wei(ETHER_AMOUNT, "ether")
        path = [w3.to_checksum_address("0x4200000000000000000000000000000000000006"),  # WETH on Base
                w3.to_checksum_address(token_address)]
        deadline = int(w3.eth.get_block("latest")["timestamp"]) + 60 * 20  # 20 min deadline

        tx = router.functions.swapExactETHForTokens(
            0,  # Min amount out (adjust for slippage)
            path,
            w3.to_checksum_address(WALLET_ADDRESS),
            deadline
        ).build_transaction({
            "from": WALLET_ADDRESS,
            "value": amount_in,
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),  # Adjust based on Base gas
            "nonce": w3.eth.get_transaction_count(WALLET_ADDRESS),
        })

        # Sign and send
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        await update.message.reply_text(f"Sniping token! Tx hash: {tx_hash.hex()}")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Main bot setup
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("snipe", snipe))
    app.run_polling()

if __name__ == "__main__":
    main()
