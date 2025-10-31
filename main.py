import os
import random
import time
import pip
import telebot
from telebot import types 
from flask import Flask, request

# --- Установка зависимостей (остается для совместимости) ---
try:
    import telebot
    from flask import Flask, request
except ImportError:
    # Устанавливаем необходимые библиотеки
    pip.main(['install', 'pytelegrambotapi', 'Flask'])
    import telebot
    from flask import Flask, request

# --- Конфигурация ---
BOT_USERNAME = "mrpolygraph_bot"

# ⚠️ ИСПОЛЬЗУЕМ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ RENDER
# BOT_TOKEN и SERVER_URL должны быть установлены в настройках Render
API_TOKEN = os.environ.get('BOT_TOKEN', '8320176221:AAE-Yhi95YxEp5P7f1_q2da9VeQeskofRCI') 
SERVER_URL = os.environ.get("SERVER_URL", "https://polygraphbot.onrender.com")

WEBHOOK_PATH = '/'
WEBHOOK_URL = f"{SERVER_URL}{WEBHOOK_PATH}"

# ⚠️ Список путей к файлам стикеров (убедитесь, что они в корне репозитория)
STICKER_FILES = [
    'sticker1.webp', 
    'sticker2.webp'
]

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__) # Инициализация Flask


# ----------------------------------------------------------------------
# 🌐 1. WEBHOOK ОБРАБОТЧИК (Критичен для Render)
# ----------------------------------------------------------------------
@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    """Обрабатывает входящие POST-запросы от Telegram."""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'OK', 200


# ----------------------------------------------------------------------
# 🖼️ 2. ФУНКЦИЯ ОТПРАВКИ КОНТЕНТА (Исправлено на send_sticker + Диагностика)
# ----------------------------------------------------------------------
def send_random_content_handler(message):
    """Общая функция для отправки случайного стикера как стикера."""
    
    if not STICKER_FILES:
         print("DEBUG: Список стикеров STICKER_FILES пуст. Проверьте конфигурацию.")
         return
         
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    selected_sticker_path = random.choice(STICKER_FILES)

    try:
        # 💡 Используем send_sticker для корректной обработки WEBP-файлов
        with open(selected_sticker_path, 'rb') as sticker_file:
            bot.send_sticker(
                chat_id=message.chat.id,
                sticker=sticker_file, # Передаем файл как 'sticker'
                reply_to_message_id=reply_id
            )
    
    # 🚨 ЛОВИМ И ЛОГИРУЕМ ТОЧНУЮ ОШИБКУ (для диагностики в логах Render)
    except FileNotFoundError:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Файл не найден по пути: {selected_sticker_path}.")
        bot.reply_to(message,
                     f"🚫 Ошибка: Файл '{selected_sticker_path}' не найден. См. лог Render.")
    
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Необработанное исключение: {type(e).__name__}: {e}")
        bot.reply_to(message,
                     f"🚫 Критическая ошибка при отправке: {e}. См. лог Render.")


# ----------------------------------------------------------------------
# 💡 3. INLINE-ОБРАБОТЧИК 
# ----------------------------------------------------------------------
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
        print(f"Ошибка в inline-обработчике: {e}")


# ----------------------------------------------------------------------
# 💬 4. ОСНОВНОЙ ОБРАБОТЧИК
# ----------------------------------------------------------------------

# 1. ОБРАБОТЧИК: /check как подпись к фото
@bot.message_handler(content_types=['photo'], regexp='^/check($|\\s.*)')
def handle_photo_caption_check(message):
    send_random_content_handler(message)


# 2. ОБРАБОТЧИК: команда /check
@bot.message_handler(commands=['check'])
def handle_check(message):
    send_random_content_handler(message)


# 3. ОБРАБОТЧИК: Все текстовые сообщения с тегом (@mrpgraph_bot)
@bot.message_handler(content_types=['text'])
def send_random_image(message):
    # Проверяем, содержит ли сообщение @mrpolygraph_bot
    if f'@{BOT_USERNAME}' in message.text:
        send_random_content_handler(message)


# ----------------------------------------------------------------------
# 🚀 5. ЗАПУСК СЕРВЕРА
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Установка вебхука перед запуском сервера
    print("--- Запуск бота ---")
    print("Удаление старого вебхука...")
    bot.remove_webhook()
    time.sleep(1) 
    print(f"Установка нового вебхука: {WEBHOOK_URL}")
    s = bot.set_webhook(url=WEBHOOK_URL)
    
    if s:
        print("Webhook установлен успешно!")
    else:
        print("Ошибка при установке Webhook.")

    # 2. Запуск Flask на порту, предоставленном Render (используем os.environ.get("PORT"))
    port = int(os.environ.get("PORT", 5000))
    print(f"--- Бот запущен и слушает порт {port} ---")
    # Gunicorn будет вызывать app
    app.run(host='0.0.0.0', port=port)
