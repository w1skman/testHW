import os
import asyncio
import logging
from waitress import serve
from flask import Flask
from telegram_bot import HotWheelsMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ HotWheels Bot is running!"

@app.route('/health')
def health():
    return "🟢 OK"

async def run_bot_async():
    """Асинхронный запуск Telegram бота"""
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found")
            return False
            
        monitor = HotWheelsMonitor(token)
        await monitor.start_bot()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        return False

def run_bot():
    """Запуск бота в отдельном потоке"""
    def start_async():
        asyncio.run(run_bot_async())
    
    bot_thread = threading.Thread(target=start_async)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("✅ Telegram Bot запущен в отдельном потоке!")

# Запускаем бот
run_bot()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Запуск production сервера на порту {port}")
    serve(app, host='0.0.0.0', port=port)
