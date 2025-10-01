import os
import asyncio
import logging
from telegram_bot import HotWheelsMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        return
    
    logger.info("🤖 Запускаю HotWheels бота...")
    monitor = HotWheelsMonitor(token)
    await monitor.start_bot()

if __name__ == "__main__":
    asyncio.run(main())
