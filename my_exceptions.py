class SendMessageErrorException(Exception):
    """Ошибка отправки сообщения функции send_message."""

    pass


class TokenValidException(Exception):
    """get_api_answer вернул не список."""

    pass


class ResponseListAreEmpty(Exception):
    """get_api_answer list is empty."""

    pass
