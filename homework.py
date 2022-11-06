import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from my_exceptions import SendMessageErrorException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = int(os.getenv('RETRY_TIME', 600))
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def logging_conf():
    """Настройки логирования для вызова в main()."""
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s, %(levelname)s, %(message)s',
                        handlers=[logging.StreamHandler(sys.stdout)])


def send_message(bot, message):
    """Отправка сообщений в телеграм чат."""
    try:
        logging.info('Отправляю сообщение в телеграм чат')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except SendMessageErrorException:
        raise Exception('Неудалось отправить сообщение')


def get_api_answer(current_timestamp) -> dict:
    """Запрос к эндпоинту API YaP."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info(f'Отправляю Запрос с датой {timestamp} к {ENDPOINT}')
        homework_status = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params)
        if homework_status.status_code != HTTPStatus.OK:
            raise Exception('Запрос к ендпоинту вернул ошибку. '
                            f'Код ответа:{homework_status.status_code}')
        return homework_status.json()
    except Exception as error:
        raise ConnectionError(f'Ошибка обращения к API Praktikum. {error}')


def check_response(response: dict) -> list:
    """Проверка ответа API YaP на корректность."""
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError('Содержимое не является списком')
    if not homework:
        logging.info('Нет новой домашней работы')
        raise IndexError('Список пуст')
    logging.info('Получен список домашних работ')
    return homework


def parse_status(homework: list) -> dict:
    """Парсим статус работы из get_api_answer."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('В ответе API нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('В ответе API нет ключа homework_status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise KeyError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов."""
    logging.info('Валидация токенов')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Токены не прошли валидацию')
        sys.exit('Токены не прошли валидацию')

    else:
        logging.info('Токены прошли валидацию')
    current_timestamp = int(time.time())
    old_status = None
    while True:
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            flag_message = 'Статус работы не изменился'
            if homeworks:
                message = parse_status(homeworks[0])
            if old_status != message:
                send_message(bot, message)
                old_status = message
                send_message(bot, message)
            logging.info('Успешно отправлен статус домашней работы')
            logging.info(flag_message)
        except TelegramError as error:
            (f'Ошибка работы программы{error}')
        except ConnectionError as err:
            (f'Ошибка работы программы {err}')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging_conf()
    main()
