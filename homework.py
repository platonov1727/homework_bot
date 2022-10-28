from http import HTTPStatus
import logging
import os
import time
from pprint import pprint

import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений в телеграм чат"""
    logging.info('Отправленно сообщение в телеграм')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logging.exception('№№№ переделывай')
        raise Exception('$$$ переделывай')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API YaP"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info('Отправляю Запрос к API YaP')
        homework_status = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params)
        if homework_status.status_code != HTTPStatus.OK:
            logging.error('Эндпоинт недоступен')
            raise Exception('Эндпоинт недоступен')
        return homework_status.json()
    except Exception:
        logging.exception('Ошибка обращения к API Praktikum')
        raise Exception('Ошибка обращения к API Praktikum')


def check_response(response):
    """Проверка ответа API YaP на корректность"""
    if isinstance(response, list):
        response = response['homeworks'][0]
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Содержимое не списочек')
    return homework


def parse_status(homework):
    """Парсим статус работы из get_api_answer"""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('В ответе API нет ключа homework_name')
        raise KeyError('В ответе API нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logging.error('В ответе API нет ключа homework_status')
        raise KeyError('В ответе API нет ключа homework_status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        logging.error('Неизвестный статус')
        raise KeyError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов"""
    bool_or_not_to_bool = all([
        PRACTICUM_TOKEN is not None, TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None
    ])
    return bool_or_not_to_bool


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    if check_tokens():
        logging.info('Токены впорядке')
        send_message(bot, 'Токены проверенны статус ОК')
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            flag_message = 'Статус работы не изменился'
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            logging.info(flag_message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
