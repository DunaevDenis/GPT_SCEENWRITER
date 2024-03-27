import logging
from telebot import TeleBot, types
from config import *
from gpt import GPT
from yandex_gpt import count_tokens_in_dialogue, get_creds, create_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=LOGS_FILE,
    filemode="w",
)

logging.info("Бот запущен")

users_history = {}
bot = TeleBot(TOKEN_BOT)
gpt = GPT()
logging.info("Переменные созданы")

# Функция для создания клавиатуры с нужными кнопочками
def create_keyboard(buttons_list):
    try:
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(*buttons_list)
        return keyboard
    except:
        logging.error("Ошибка создания клавиатуры")


# Приветственное сообщение /start
@bot.message_handler(commands=['start', "help"])
def start(message):
    logging.info(f"{message.chat.id}: {message.text}")
    user_name = message.from_user.first_name
    bot_answer = {"/start" : f"Привет, {user_name}! Я бот-сценарист и могу написать историю по твоему желанию👾\n"
                          f"Чтобы начать жми /new_story.\n",
                  "/help" : "Чтобы приступить к написанию истории нажми /new_story а затем выбери жанр, героя, сеттинг "
                            "и можешь приступать к написанию истории /begin, при завершении истории нажми /end",}
    bot.send_message(message.chat.id, bot_answer[message.text],
                     reply_markup=create_keyboard(["/new_story"]))

# Команда /debug
@bot.message_handler(commands=['debug'])
def debug(message):
    with open(LOGS_FILE, "rb") as f:
        bot.send_document(message.chat.id, f)


@bot.message_handler(commands=["new_story"])
def new_story(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "Выберите жанр истории или впишите свой", reply_markup=create_keyboard(["Хоррор", "Комедия", "Боевик"]))
    if user_id not in users_history:
        users_history[user_id] = {"text": "", "tokens": 0, "session_id": 1}
    else:
        users_history[user_id]["session_id"] += 1
        users_history[user_id]["tokens"] = 0
    bot.register_next_step_handler(message, genre)


def genre(message):
    try:
        user_id = message.from_user.id
        if message.content_type != "text":
            bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
            bot.send_message(message.chat.id, "Выберите жанр истории или впишите свой",
                             reply_markup=create_keyboard(["Хоррор", "Комедия", "Боевик"]))
            bot.register_next_step_handler(message, genre)
            return
        users_history[user_id]["genre"] = message.text
        bot.send_message(message.chat.id, "Выбери героя или впишите своего", reply_markup=create_keyboard(["Шрек", "Скубиду", "Даша путешественница", "Аянами Рей"]))
        bot.register_next_step_handler(message, hero)
    except Exception as e:
        logging.error(f"Ошибка добавление пользователя в БД или сохранения жанра: {e}")


def hero(message):
    try:
        user_id = message.from_user.id
        if message.content_type != "text":
            bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
            bot.send_message(message.chat.id, "Выбери героя или впишите своего", reply_markup=create_keyboard(["Шрек", "Скубиду", "Даша путешественница", "Аянами Рей"]))
            bot.register_next_step_handler(message, hero)
            return
        users_history[user_id]["hero"] = message.text
        bot.send_message(message.chat.id, f"Выбери сеттинг:\n\nГород - {SETTING_DICT['Город']}.\n\n"
                                          f"Природа - {SETTING_DICT['Природа']}.\n\nМагия - {SETTING_DICT['Магия']}",
                         reply_markup=create_keyboard(["Город", "Природа", "Магия"]))
        bot.register_next_step_handler(message, setting)
    except Exception as e:
        logging.error(f"Ошибка сохранения героя: {e}")


def setting(message):
    try:
        user_id = message.from_user.id
        if message.content_type != "text":
            bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
            bot.send_message(message.chat.id, "Выбери сеттинг или впишите свой",
                             reply_markup=create_keyboard(["Город", "Природа", "Магия"]))
            bot.register_next_step_handler(message, setting)
            return
        if message.text not in ["Город", "Природа", "Магия"]:
            bot.send_message(message.chat.id, "Выбери сеттинг или впишите свой",
                             reply_markup=create_keyboard(["Город", "Природа", "Магия"]))
            bot.register_next_step_handler(message, setting)
            return
        users_history[user_id]["setting"] = message.text
        bot.send_message(message.chat.id, "Хотите что нибудь добавить? Если нет то нажмите /begin чтобы начать историю", reply_markup=create_keyboard(["/begin"]))
        bot.register_next_step_handler(message, begin)
    except Exception as e:
        logging.error(f"Ошибка сохранения сеттинга: {e}")


@bot.message_handler(commands=["begin"])
def begin(message):
    try:
        user_id = message.from_user.id
        if message.content_type != "text":
            bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
            bot.send_message(message.chat.id,
                             "Хотите что нибудь добавить? Если нет то нажмите /begin чтобы начать историю",
                             reply_markup=create_keyboard(["/begin"]))
            bot.register_next_step_handler(message, begin)
            return
        if user_id not in users_history:
            bot.send_message(message.chat.id, "Вас нет в базе данных, запрос не выполнен")
            new_story(message)
            return
        if "setting" not in users_history[user_id] or "genre" not in users_history[user_id] or "hero" not in users_history[user_id]:
            bot.send_message(message.chat.id, "Выберите жанр, героя и сеттинг")
            new_story(message)
            return
        if message.text != "/begin":
            bot.send_message(message.chat.id, "Всё учтем!")
            users_history[user_id]['additional_info'] = message.text
        get_promt(message)
    except Exception as e:
        logging.error(f"Ошибка /begin {e}")


# Получение задачи от пользователя или продолжение решения

def get_promt(message):
    user_id = message.from_user.id
    logging.info(f"Получен запрпос\n{user_id}:{message.text}")

    try:
        if len(users_history) > MAX_USERS:
            bot.send_message(message.chat.id, "Превышено допустимое количество пользователей")
            return

        if user_id not in users_history:
            new_story(message)
            return

        content = users_history[user_id]["text"]
        tokens = users_history[user_id]["tokens"]
        session_id = users_history[user_id]["session_id"]

        if session_id >= MAX_SESSIONS:
            bot.send_message(message.chat.id, "Вы превысили количество сессий")
            return
        # Получаем текст сообщения от пользователя
        user_request = message.text

        # Сохраняем промт пользовател

        prompt_dict = [
            {"role": "user", "content": user_request},
            {"role": "assistant", "content": ""}
        ]

        if count_tokens_in_dialogue(prompt_dict) >= MAX_TOKENS:
            bot.send_message(message.chat.id, "Слижком длинный запрос")
            bot.register_next_step_handler(message, get_promt)

        if user_request == "/begin":
            prompt_dict[0]["content"] = create_prompt(users_history, user_id)
        if user_request == "/end":
            prompt_dict[0]["content"] = "Закончи историю"

        prompt_dict[1]["content"] = content

        all_tokens = tokens + count_tokens_in_dialogue(prompt_dict)
        if is_tokens_limit(all_tokens, message.chat.id):
            return

        users_history[user_id]["tokens"] += all_tokens

        ### GPT: проверка ошибок и обработка ответа
        token, folder_id = get_creds()
        status, answer = gpt.ask_gpt(prompt_dict, token, folder_id)

        if not status:
            logging.info(f"{user_id}: {answer}")
            bot.send_message(user_id, text=answer)
            return

        token_prompt = [{
                "role": "user",
                "content": answer},]

        users_history[user_id]["tokens"] += count_tokens_in_dialogue(token_prompt)
        users_history[user_id]["text"] += answer

        if user_request != "/end":
            bot.send_message(user_id, text=prompt_dict[1]["content"] + answer, reply_markup=create_keyboard(["/end"]))
            bot.register_next_step_handler(message, get_promt)
        else:
            bot.send_message(user_id, text=prompt_dict[1]["content"] + answer,
                             reply_markup=create_keyboard(["/new_story"]))

        logging.info("Пользователь получил ответ")



    except Exception as e:
        logging.error(f"Ошибка запроса GPT: {e}")
        bot.send_message(user_id, "Ошибка запроса GPT", reply_markup=create_keyboard(["/new_story"]))


def is_tokens_limit(all_token, chat_id):
    # Получаем из таблицы размер текущей сессии в токенах
    try:
        tokens_of_session = all_token

        # В зависимости от полученного числа выводим сообщение
        if tokens_of_session >= MAX_TOKENS_IN_SESSION:
                bot.send_message(
                    chat_id,
                    f'Вы израсходовали все токены в этой сессии. Вы можете начать новую, введя help_with')
                return True

        elif tokens_of_session + 50 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше 50 токенов
            bot.send_message(
                chat_id,
                f'Вы приближаетесь к лимиту в {MAX_TOKENS_IN_SESSION} токенов в этой сессии. '
                f'Ваш запрос содержит суммарно {tokens_of_session} токенов.')

        elif tokens_of_session / 2 >= MAX_TOKENS_IN_SESSION:  # Если осталось меньше половины
            bot.send_message(
                chat_id,
                f'Вы использовали больше половины токенов в этой сессии. '
                f'Ваш запрос содержит суммарно {tokens_of_session} токенов.'
            )
        return False
    except Exception as e:
        logging.error(f"Ошибка подсчета токенов {e}")

bot.polling()