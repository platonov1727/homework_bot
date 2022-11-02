import logging
import os
import sys
import time
from http import HTTPStatus
from my_exceptions import GetApiAnswerReturnedNotList, SendMessageErrorException
import requests
from dotenv import load_dotenv
from telegram import Bot

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
    """Настройки логирования."""
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

def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API YaP."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logging.info(f'Отправляю Запрос с датой {timestamp} к {ENDPOINT}')
        homework_status = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params)
        if homework_status.status_code != HTTPStatus.OK:
            raise Exception('Эндпоинт недоступен')
        return homework_status.json()
    except Exception:
        raise ConnectionError('Ошибка обращения к API Praktikum')


def check_response(response):
    """Проверка ответа API YaP на корректность."""
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError('Содержимое не является списком')
    if not homework:
        logging.info('Нет новой домашней работы')
        raise Exception('список пуст')
    logging.info('Получен список домашних работ')
    return homework



def parse_status(homework):
    """Парсим статус работы из get_api_answer."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        logging.error('В ответе API нет ключа homework_name')
        raise KeyError('В ответе API нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logging.error('В ответе API нет ключа homework_status')
        raise KeyError('В ответе API нет ключа homework_status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        logging.error('Неизвестный статус')
        raise KeyError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов."""
    bool_or_not_to_bool = all([
        PRACTICUM_TOKEN is not None, TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None
    ])
    return bool_or_not_to_bool


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Токены не прошли валидацию')
        sys.exit('Токены не прошли валидацию')
    else:
        logging.info('Токены прошли валидацию')
    current_timestamp = int(time.time())
    while True:
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            flag_message = 'Статус работы не изменился'
            if homeworks:
                message = parse_status(homeworks)
                send_message(bot, message)
                logging.info('Успешно отправлен статус домашней работы')
            logging.info(flag_message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging_conf()
    main()

