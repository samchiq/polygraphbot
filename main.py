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

# 💾 Кэш file_id стикеров (заполняется при старте)
STICKER_FILE_IDS = []

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
# 🌐 1. WEBHOOK ОБРАБОТЧИК
# ----------------------------------------------------------------------
@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обрабатывает входящие POST-запросы от Telegram."""
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            logger.info(f"📥 Получен webhook от Telegram (длина: {len(json_string)})")

            update = telebot.types.Update.de_json(json_string)
            logger.info(f"✅ Webhook распарсен, update_id: {update.update_id}")

            # Передаём update в telebot для нормальной маршрутизации — это позволит
            # сработать inline-обработчикам и другим зарегистрированным хендлерам.
            try:
                bot.process_new_updates([update])
                logger.info("✅ Update передан telebot.process_new_updates")
            except Exception as e:
                logger.error(f"❌ Ошибка при передаче update в telebot: {e}", exc_info=True)
                # При желании можно вручную обработать inline_query:
                # if update.inline_query:
                #     handle_inline_query_manually(update.inline_query)

            return '', 200
    except Exception as e:
        logger.error(f"❌ ОШИБКА в webhook: {e}", exc_info=True)
        return 'ERROR', 500

    logger.warning("⚠️ Получен запрос без JSON")
    return 'OK', 200


# ----------------------------------------------------------------------
# 🖼️ 2. ФУНКЦИЯ ОТПРАВКИ КОНТЕНТА
# ----------------------------------------------------------------------
def send_random_content_handler(message):
    """Отправляет случайный стикер, используя кэшированный file_id."""

    # Если есть кэш - используем его
    if STICKER_FILE_IDS:
        reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
        selected_file_id = random.choice(STICKER_FILE_IDS)

        try:
            # Отправляем по file_id - мгновенно, без повторной загрузки!
            bot.send_sticker(
                chat_id=message.chat.id,
                sticker=selected_file_id,
                reply_to_message_id=reply_id
            )
            return
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке по file_id: {e}")

    # Fallback: если кэша нет, загружаем файл напрямую
    logger.warning("⚠️ Кэш file_id пуст, загружаем файл напрямую")
    existing_stickers = [path for path in LOCAL_STICKER_PATHS if os.path.exists(path)]

    if not existing_stickers:
        logger.error(f"❌ Файлы стикеров не найдены!")
        bot.reply_to(message, "🚫 Ошибка: Стикеры недоступны.")
        return

    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    selected_sticker = random.choice(existing_stickers)

    try:
        with open(selected_sticker, 'rb') as sticker_file:
            bot.send_sticker(
                chat_id=message.chat.id,
                sticker=sticker_file,
                reply_to_message_id=reply_id
            )
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке стикера: {e}", exc_info=True)
        bot.reply_to(message, f"🚫 Ошибка при отправке.")


# ----------------------------------------------------------------------
# 3. INLINE-ОБРАБОТЧИК
# ----------------------------------------------------------------------
print("=" * 60, flush=True)
print("📋 REGISTERING INLINE HANDLER", flush=True)
print("=" * 60, flush=True)


@bot.inline_handler(lambda query: True)
def query_text(inline_query):
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
    except Exception as e:
        logger.error(f"❌ Ошибка в inline-обработчике: {e}", exc_info=True)


print("✅ Inline handler registered", flush=True)
sys.stdout.flush()


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
    send_random_content_handler(message)


print("✅ Handler registered: commands=['check']", flush=True)
sys.stdout.flush()


@bot.message_handler(content_types=['photo'], regexp='^/check($|\\s.*)')
def handle_photo_caption_check(message):
    send_random_content_handler(message)


print("✅ Handler registered: photo + /check", flush=True)
sys.stdout.flush()


@bot.message_handler(content_types=['text'])
def send_random_image(message):
    if f'@{BOT_USERNAME}' in message.text:
        send_random_content_handler(message)


print("✅ Handler registered: text (with @mention check)", flush=True)
sys.stdout.flush()


# Убираем fallback handler - он больше не нужен
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
def upload_stickers_and_cache_ids():
    """Загружает стикеры один раз и кэширует их file_id."""
    global STICKER_FILE_IDS
    STICKER_FILE_IDS = []

    logger.info("📤 Загрузка стикеров и кэширование file_id...")

    # Нужен chat_id для отправки тестовых стикеров
    # Используем переменную окружения или отправляем в Saved Messages
    test_chat_id = os.environ.get('ADMIN_CHAT_ID')

    if not test_chat_id:
        logger.warning("⚠️ ADMIN_CHAT_ID не установлен, пропускаем кэширование file_id")
        logger.warning("⚠️ Будет использоваться загрузка файлов каждый раз")
        return

    for sticker_path in LOCAL_STICKER_PATHS:
        try:
            if not os.path.exists(sticker_path):
                logger.error(f"   ❌ {sticker_path} не найден!")
                continue

            with open(sticker_path, 'rb') as sticker_file:
                # Отправляем стикер для получения file_id
                msg = bot.send_sticker(chat_id=test_chat_id, sticker=sticker_file)
                file_id = msg.sticker.file_id
                STICKER_FILE_IDS.append(file_id)
                logger.info(f"   ✅ {sticker_path} → file_id кэширован")

                # Удаляем тестовое сообщение
                try:
                    bot.delete_message(test_chat_id, msg.message_id)
                except:
                    pass

        except Exception as e:
            logger.error(f"   ❌ Ошибка загрузки {sticker_path}: {e}")

    logger.info(f"✅ Кэшировано file_id: {len(STICKER_FILE_IDS)} стикеров")


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

    # Загружаем стикеры и кэшируем file_id
    upload_stickers_and_cache_ids()

    # Установка webhook
    logger.info("🌐 Установка webhook...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        # Важно: разрешаем получение inline_query в allowed_updates
        s = bot.set_webhook(url=WEBHOOK_URL, allowed_updates=['message', 'inline_query', 'edited_message'])

        if s:
            logger.info(f"   ✅ Webhook установлен: {WEBHOOK_URL} (allowed_updates includes inline_query)")
        else:
            logger.error("   ❌ Ошибка установки webhook")
    except Exception as e:
        logger.error(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("✅ БОТ ГОТОВ К РАБОТЕ")
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
