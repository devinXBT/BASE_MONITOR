import os
from telegram import Bot

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7702711510:AAHwIAcx1z_Luv_-IjRaMWJq4UgTsekht2Y")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6442285058")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Send a test message
async def send_test_message():
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🚀 Test message: Your bot is working!")
        print("Test message sent successfully!")
    except Exception as e:
        print(f"Failed to send message: {e}")

# Run the script
if __name__ == "__main__":
    import asyncio
    asyncio.run(send_test_message())
