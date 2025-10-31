import os
import random
import time
import pip
import telebot
from telebot import types 
from flask import Flask, request

# --- Установка зависимостей ---
try:
    import telebot
    from flask import Flask, request
except ImportError:
    pip.main(['install', 'pytelegrambotapi', 'Flask'])
    import telebot
    from flask import Flask, request

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

# 💡 НОВАЯ ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ: Здесь будут храниться ID стикеров Telegram
# Это ключевой элемент обхода проблемы.
STICKER_IDS = [] 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__) # Инициализация Flask


# ----------------------------------------------------------------------
# 🌐 1. WEBHOOK ОБРАБОТЧИК 
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
# 🖼️ 2. ФУНКЦИЯ ОТПРАВКИ КОНТЕНТА (Используем File ID)
# ----------------------------------------------------------------------
def send_random_content_handler(message):
    """Общая функция для отправки случайного стикера, используя File ID."""
    global STICKER_IDS # Используем глобальный список ID
    
    if not STICKER_IDS:
         print("DEBUG: Список STICKER_IDS пуст. Стикеры не были загружены при запуске!")
         bot.reply_to(message, "🚫 Ошибка: Стикеры не были загружены при старте сервера.")
         return
         
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    
    # 💡 Выбираем File ID, а не путь к файлу
    selected_sticker_id = random.choice(STICKER_IDS)

    try:
        # 💡 Отправляем стикер по ID, что гарантированно работает на Render
        bot.send_sticker(
            chat_id=message.chat.id,
            sticker=selected_sticker_id, 
            reply_to_message_id=reply_id
        )
    
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Необработанное исключение при отправке ID: {type(e).__name__}: {e}")
        bot.reply_to(message,
                     f"🚫 Критическая ошибка при отправке стикера по ID: {e}. См. лог Render.")


# ----------------------------------------------------------------------
# 3. INLINE-ОБРАБОТЧИК (без изменений)
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
# 💬 4. ОСНОВНОЙ ОБРАБОТЧИК (без изменений)
# ----------------------------------------------------------------------
@bot.message_handler(content_types=['photo'], regexp='^/check($|\\s.*)')
def handle_photo_caption_check(message):
    send_random_content_handler(message)


@bot.message_handler(commands=['check'])
def handle_check(message):
    send_random_content_handler(message)


@bot.message_handler(content_types=['text'])
def send_random_image(message):
    if f'@{BOT_USERNAME}' in message.text:
        send_random_content_handler(message)


# ----------------------------------------------------------------------
# 🚀 5. ЗАПУСК СЕРВЕРА
# ----------------------------------------------------------------------

# 💡 НОВАЯ ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ СТИКЕРОВ
def upload_stickers():
    """Загружает стикеры в Telegram, получает их ID и сохраняет в STICKER_IDS."""
    global STICKER_IDS
    STICKER_IDS = []
    
    print("--- Загрузка стикеров на сервера Telegram ---")
    
    for path in LOCAL_STICKER_PATHS:
        try:
            with open(path, 'rb') as sticker_file:
                # 💡 Отправляем стикер самому себе или в любой чат для получения file_id
                # Но мы просто используем send_sticker, чтобы Telegram вернул объект Message
                
                # Примечание: Telegram вернет объект Message, из которого мы возьмем file_id
                message = bot.send_sticker(
                    chat_id=bot.get_me().id, # Отправляем стикер самому боту (в его личный чат)
                    sticker=sticker_file
                )
                
                file_id = message.sticker.file_id
                STICKER_IDS.append(file_id)
                print(f"✅ Стикер {path} загружен. ID: {file_id}")
                
        except FileNotFoundError:
            print(f"❌ ОШИБКА: Локальный файл стикера не найден: {path}. Проверьте репозиторий!")
            # Если FileNotFoundError сработает здесь, это означает, что стикеров нет в контейнере Render
        except Exception as e:
            print(f"❌ ОШИБКА: Не удалось загрузить стикер {path}. Ошибка: {e}")
            
    # Удаляем сообщения, которые бот отправил сам себе для чистоты
    try:
        for message_id in range(message.message_id, message.message_id - len(LOCAL_STICKER_PATHS), -1):
             bot.delete_message(bot.get_me().id, message_id)
    except Exception:
        pass
        
    print(f"--- Загрузка завершена. Всего ID стикеров: {len(STICKER_IDS)} ---")


if __name__ == "__main__":
    
    # 0. Диагностика пути и файлов (Оставляем для последней проверки)
    print(f"--- Текущая рабочая директория: {os.getcwd()} ---")
    print(f"--- Файлы в текущей директории: {os.listdir()} ---")
    
    # 1. Загрузка стикеров на Telegram при старте
    # Эта функция должна быть выполнена первой, чтобы заполнить STICKER_IDS
    upload_stickers() 
    
    # 2. Установка вебхука
    print("--- Установка вебхука ---")
    bot.remove_webhook()
    time.sleep(1) 
    print(f"Установка нового вебхука: {WEBHOOK_URL}")
    s = bot.set_webhook(url=WEBHOOK_URL)
    
    if s:
        print("Webhook установлен успешно!")
    else:
        print("Ошибка при установке Webhook.")

    # 3. Запуск Flask
    port = int(os.environ.get("PORT", 5000))
    print(f"--- Бот запущен и слушает порт {port} ---")
    app.run(host='0.0.0.0', port=port)
