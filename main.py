import os
import sys
import random
import time
import logging
import telebot
from telebot import types 
from flask import Flask, request

# ==========================================
# 🔧 НАСТРОЙКА ЛОГИРОВАНИЯ (КРИТИЧЕСКИ ВАЖНО ДЛЯ RENDER!)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Переопределяем существующую конфигурацию
)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Отключаем буферизацию stdout
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

# Также настроим логирование для telebot
telebot_logger = logging.getLogger('TeleBot')
telebot_logger.setLevel(logging.INFO)

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
BOT_USERNAME = "mrpolygraph_bot"

# ⚠️ ИСПОЛЬЗУЕМ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ RENDER
API_TOKEN = os.environ.get('BOT_TOKEN', '8320176221:AAE-Yhi95YxEp5P7f1_q2da9VeQeskofRCI') 
SERVER_URL = os.environ.get("SERVER_URL", "https://polygraphbot.onrender.com")

WEBHOOK_PATH = '/'
WEBHOOK_URL = f"{SERVER_URL}{WEBHOOK_PATH}"

# ⚠️ Список путей к локальным стикерам
LOCAL_STICKER_PATHS = [
    'sticker1.webp', 
    'sticker2.webp'
]

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# КРИТИЧЕСКИ ВАЖНО: Логи СРАЗУ после инициализации
print("=" * 60, flush=True)
print("🤖 BOT INITIALIZATION STARTED", flush=True)
print("=" * 60, flush=True)
logger.info("🤖 TeleBot инициализирован")
logger.info("🌐 Flask app создан")
sys.stdout.flush()


# ----------------------------------------------------------------------
# 🌐 1. WEBHOOK ОБРАБОТЧИК (ИСПРАВЛЕННАЯ ВЕРСИЯ)
# ----------------------------------------------------------------------
@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обрабатывает входящие POST-запросы от Telegram."""
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            logger.info(f"📥 Получен webhook, update_id: {update.update_id}")

            # -----------------------------------------------------------
            # 🔍 ДИАГНОСТИЧЕСКОЕ ЛОГИРОВАНИЕ (из вашего кода)
            # -----------------------------------------------------------
            if update.message:
                msg = update.message
                logger.info(f"   Тип: Message, chat_id: {msg.chat.id}, user: {msg.from_user.id}")
                logger.info(f"   Текст: '{msg.text}' (Content type: {msg.content_type})")
            
            elif update.inline_query:
                query = update.inline_query
                logger.info(f"   Тип: InlineQuery, user: {query.from_user.id}")
                logger.info(f"   Запрос: '{query.query}'")
            
            else:
                logger.info(f"   Тип: Другой (не message и не inline query)")

            # -----------------------------------------------------------
            # ✅ ЕДИНСТВЕННЫЙ ПРАВИЛЬНЫЙ ВЫЗОВ ОБРАБОТЧИКА
            # -----------------------------------------------------------
            # Удаляем старые 'process_new_messages' и 'Попытка 2'
            # Вызываем ОДИН раз 'process_new_updates' для ВСЕГО объекта 'update'
            try:
                bot.process_new_updates([update])
                logger.info("   ✅ process_new_updates выполнен")
            except Exception as e:
                logger.error(f"   ❌ Ошибка во время process_new_updates: {e}", exc_info=True)

            return '', 200
            
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в webhook: {e}", exc_info=True)
        return 'ERROR', 500
    
    logger.warning("⚠️ Получен запрос без JSON")
    return 'OK', 200


# ----------------------------------------------------------------------
# 🖼️ 2. ФУНКЦИЯ ОТПРАВКИ КОНТЕНТА
# ----------------------------------------------------------------------
def send_random_content_handler(message):
    """Отправляет случайный стикер из локальных файлов."""
    logger.info(f"🎯 send_random_content_handler вызван для chat_id={message.chat.id}, user={message.from_user.id}")
    
    # Проверяем, что файлы существуют
    existing_stickers = [path for path in LOCAL_STICKER_PATHS if os.path.exists(path)]
    
    if not existing_stickers:
        logger.error(f"❌ Ни один файл стикера не найден!")
        logger.error(f"   Текущая директория: {os.getcwd()}")
        logger.error(f"   Файлы в директории: {os.listdir()}")
        bot.reply_to(message, "🚫 Ошибка: Файлы стикеров не найдены на сервере.")
        return
    
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    
    # Выбираем случайный стикер
    selected_sticker = random.choice(existing_stickers)
    logger.info(f"✅ Выбран стикер: {selected_sticker}")

    try:
        # Открываем файл и отправляем как стикер
        with open(selected_sticker, 'rb') as sticker_file:
            logger.info(f"📤 Отправляем стикер в чат {message.chat.id}...")
            result = bot.send_sticker(
                chat_id=message.chat.id,
                sticker=sticker_file, 
                reply_to_message_id=reply_id
            )
            logger.info(f"✅ Стикер отправлен успешно! Message ID: {result.message_id}")
        
    except FileNotFoundError:
        logger.error(f"❌ Файл не найден: {selected_sticker}")
        bot.reply_to(message, f"🚫 Файл {selected_sticker} не найден.")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке стикера: {type(e).__name__}: {e}", exc_info=True)
        bot.reply_to(message, f"🚫 Ошибка при отправке: {e}")


# ----------------------------------------------------------------------
# 3. INLINE-ОБРАБОТЧИК
# ----------------------------------------------------------------------
@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    logger.info(f"🔍 Получен inline query от {inline_query.from_user.id}: '{inline_query.query}'")
    user_query = inline_query.query

    if user_query:
        title_text = f"Проверить: {user_query}"
        message_content = f"@{BOT_USERNAME} {user_query}"
    else:
        title_text = "Нажмите для проверки"
        message_content = f"@{BOT_USERNAME} "

    r = types.InlineQueryResultArticle(
        id='1',
        title=title_text,
        input_message_content=types.InputTextMessageContent(message_text=message_content)
    )

    try:
        bot.answer_inline_query(inline_query.id, [r], cache_time=0)
        logger.info(f"✅ Inline query обработан")
    except Exception as e:
        logger.error(f"❌ Ошибка в inline-обработчике: {e}", exc_info=True)


# ----------------------------------------------------------------------
# 💬 4. РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ (ДО ВЫЗОВА setup_bot!)
# ----------------------------------------------------------------------
print("=" * 60, flush=True)
print("📋 REGISTERING MESSAGE HANDLERS", flush=True)
print("=" * 60, flush=True)
logger.info("📋 РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ КОМАНД")
sys.stdout.flush()

@bot.message_handler(commands=['check'])
def handle_check(message):
    logger.info(f"💬 ОБРАБОТЧИК /check СРАБОТАЛ! user_id={message.from_user.id}")
    send_random_content_handler(message)

print("✅ Handler registered: commands=['check']", flush=True)
logger.info("✅ Обработчик: commands=['check']")
sys.stdout.flush()


@bot.message_handler(content_types=['photo'], regexp='^/check($|\\s.*)')
def handle_photo_caption_check(message):
    logger.info(f"📸 ОБРАБОТЧИК photo+/check СРАБОТАЛ! user_id={message.from_user.id}")
    send_random_content_handler(message)

print("✅ Handler registered: photo + /check", flush=True)
logger.info("✅ Обработчик: photo + /check")
sys.stdout.flush()


@bot.message_handler(content_types=['text'])
def send_random_image(message):
    logger.info(f"📝 ОБРАБОТЧИК text СРАБОТАЛ от {message.from_user.id}: '{message.text[:50]}'")
    if f'@{BOT_USERNAME}' in message.text:
        logger.info(f"✅ Найдено упоминание @{BOT_USERNAME}")
        send_random_content_handler(message)
    else:
        logger.info(f"⏭️ Сообщение не содержит @{BOT_USERNAME}")

print("✅ Handler registered: text", flush=True)
logger.info("✅ Обработчик: content_types=['text']")
sys.stdout.flush()


@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'document', 'sticker'])
def fallback_handler(message):
    logger.warning(f"⚠️ FALLBACK сработал для {message.from_user.id}")
    bot.reply_to(message, "Попробуйте команду /check")

print("✅ Handler registered: fallback", flush=True)
logger.info("✅ Обработчик: fallback (func=lambda)")
print("=" * 60, flush=True)
print("📋 ALL HANDLERS REGISTERED!", flush=True)
print("=" * 60, flush=True)
sys.stdout.flush()


# ----------------------------------------------------------------------
# 📝 5. HEALTHCHECK ENDPOINT
# ----------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    """Endpoint для проверки работоспособности бота."""
    existing_stickers = [path for path in LOCAL_STICKER_PATHS if os.path.exists(path)]
    status = {
        'status': 'running',
        'stickers_found': len(existing_stickers),
        'sticker_files': existing_stickers,
        'current_dir': os.getcwd(),
        'all_files': os.listdir()[:20],  # Первые 20 файлов
        'webhook_url': WEBHOOK_URL
    }
    logger.info(f"🏥 Health check запрошен")
    return status, 200


# ----------------------------------------------------------------------
# 🚀 6. ИНИЦИАЛИЗАЦИЯ БОТА (ВЫПОЛНЯЕТСЯ ВСЕГДА!)
# ----------------------------------------------------------------------
def setup_bot():
    """Настройка бота - вызывается при импорте модуля"""
    logger.info("=" * 60)
    logger.info("🚀 ИНИЦИАЛИЗАЦИЯ TELEGRAM БОТА")
    logger.info("=" * 60)
    logger.info(f"📁 Рабочая директория: {os.getcwd()}")
    logger.info(f"🎨 Ожидаемые стикеры: {LOCAL_STICKER_PATHS}")
    
    # Проверяем стикеры
    for sticker_path in LOCAL_STICKER_PATHS:
        if os.path.exists(sticker_path):
            size = os.path.getsize(sticker_path)
            logger.info(f"   ✅ {sticker_path} ({size} байт)")
        else:
            logger.error(f"   ❌ {sticker_path} НЕ НАЙДЕН!")
    
    # Установка webhook
    logger.info("🌐 Установка webhook...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        s = bot.set_webhook(url=WEBHOOK_URL)
        
        if s:
            logger.info(f"   ✅ Webhook установлен: {WEBHOOK_URL}")
            webhook_info = bot.get_webhook_info()
            logger.info(f"   📊 Pending updates: {webhook_info.pending_update_count}")
            if webhook_info.last_error_date:
                logger.warning(f"   ⚠️ Ошибка: {webhook_info.last_error_message}")
        else:
            logger.error("   ❌ Ошибка установки webhook")
    except Exception as e:
        logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
    
    logger.info("=" * 60)
    logger.info("✅ БОТА ГОТОВ К РАБОТЕ")
    logger.info("=" * 60)
    sys.stdout.flush()


# ⚠️ ВЫЗЫВАЕМ setup_bot() СРАЗУ при импорте
setup_bot()


# ----------------------------------------------------------------------
# 🚀 7. ЗАПУСК FLASK (только при прямом запуске)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск Flask в режиме разработки на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
