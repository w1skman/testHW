import sqlite3
import requests
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = 1254080795

class HotWheelsMonitor:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.init_db()
        self.setup_handlers()
        
        self.products = [
            {
                'id': 'hw_265193', 
                'name': 'Hot Wheels Basic Car',
                'product_id': '265193',
                'store_id': '3223',
                'store': 'Лента (твой магазин)'
            },
        ]

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect('hotwheels.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                store_id TEXT,
                quantity INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                old_quantity INTEGER,
                new_quantity INTEGER,
                increase INTEGER,
                acknowledged BOOLEAN DEFAULT FALSE,
                message_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user_id = update.effective_user.id
        
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ У вас нет доступа к этому боту")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 На данный момент", callback_data="current_stock")],
            [InlineKeyboardButton("📈 Статистика", callback_data="statistics_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 Панель управления Hot Wheels Monitor\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != ADMIN_CHAT_ID:
            await query.edit_message_text("❌ У вас нет доступа")
            return

        if query.data == "current_stock":
            await self.send_current_stock(query)
        elif query.data == "statistics_menu":
            await self.show_statistics_menu(query)
        elif query.data.startswith("stats_"):
            period = query.data.replace("stats_", "")
            await self.show_statistics(query, period)
        elif query.data == "back_to_main":
            await self.back_to_main(query)

    async def send_current_stock(self, query):
        """Отправка текущего остатка"""
        await query.edit_message_text("🔄 Выполняю запрос...")
        
        product = self.products[0]
        current_stock = await self.get_current_stock(product['product_id'], product['store_id'])
        
        if current_stock is not None:
            message = (
                f"📊 Остаток на данный момент:\n"
                f"🎯 {product['name']}\n"
                f"🏪 {product['store']}\n"
                f"📦 В наличии: {current_stock} шт.\n"
                f"⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
        else:
            message = "❌ Ошибка при получении остатка"
        
        keyboard = [
            [InlineKeyboardButton("📊 На данный момент", callback_data="current_stock")],
            [InlineKeyboardButton("📈 Статистика", callback_data="statistics_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def show_statistics_menu(self, query):
        """Меню выбора статистики"""
        keyboard = [
            [InlineKeyboardButton("📅 Неделя", callback_data="stats_week")],
            [InlineKeyboardButton("📅 Месяц", callback_data="stats_month")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📈 Выберите период для статистики:",
            reply_markup=reply_markup
        )

    async def show_statistics(self, query, period):
        """Показать статистику за период"""
        await query.edit_message_text("📊 Формирую статистику...")
        
        stats = self.get_statistics(period)
        
        if not stats:
            message = "📊 Данных за выбранный период нет"
        else:
            message = f"📈 Статистика за {period}:\n\n"
            previous_stock = None
            
            for date_str, stock in stats:
                if previous_stock is not None and stock > previous_stock:
                    message += f"{date_str} - {stock} шт. 🚀 ЗАВОЗ!\n"
                else:
                    message += f"{date_str} - {stock} шт.\n"
                previous_stock = stock
        
        keyboard = [
            [InlineKeyboardButton("📅 Неделя", callback_data="stats_week")],
            [InlineKeyboardButton("📅 Месяц", callback_data="stats_month")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    def get_statistics(self, period):
        """Получить статистику из БД"""
        conn = sqlite3.connect('hotwheels.db')
        cursor = conn.cursor()
        
        if period == "week":
            date_filter = datetime.now() - timedelta(days=7)
        else:  # month
            date_filter = datetime.now() - timedelta(days=30)
        
        cursor.execute('''
            SELECT DATE(timestamp), MAX(quantity) 
            FROM stock_history 
            WHERE product_id = ? AND timestamp > ?
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp)
        ''', (self.products[0]['id'], date_filter))
        
        stats = cursor.fetchall()
        conn.close()
        return stats

    async def back_to_main(self, query):
        """Возврат в главное меню"""
        keyboard = [
            [InlineKeyboardButton("📊 На данный момент", callback_data="current_stock")],
            [InlineKeyboardButton("📈 Статистика", callback_data="statistics_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 Панель управления Hot Wheels Monitor\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def get_current_stock(self, product_id, store_id):
        """Получение остатка через API Ленты"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
            }
            
            params = {'id': product_id, 'storeId': store_id}
            url = 'https://lenta.com/api-gateway/v1/catalog/items/stock'
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            stock = data.get('stock', 0)
            
            logger.info(f"📦 API Ленты: остаток {stock} шт.")
            return stock
            
        except Exception as e:
            logger.error(f"❌ Ошибка API: {e}")
            return None

    async def start_bot(self):
        """Запуск бота"""
        logger.info("🤖 Запускаю Telegram бота...")
        await self.application.run_polling()
