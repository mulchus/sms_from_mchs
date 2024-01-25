import asks
import asyncclick as click
import trio

from environs import Env
from contextlib import suppress
from contextvars import ContextVar
from mock import patch


class SmscApiError(Exception):
    def __init__(self, message, extra_info=None):
        super().__init__(message)
        # self.extra_info = extra_info
        

@click.command()
@click.option(
    '--login',
    required=True,
    help='логин с сайта smsc.ru',
    envvar='SMSC_LOGIN',
)
@click.option(
    '--psw',
    required=True,
    help='пароль с сайта smsc.ru',
    envvar='SMSC_PASSWORD',
)
@click.option(
    '--valid',
    help='время жизни СМС-сообщения, если не доставлено сразу, часов',
    type=int,
    envvar='SMSC_VALID',
    default=1,
)
@click.option(
    '--phones',
    required=True,
    help='список телефонов через запятую, с +7 или 8',
    envvar='PHONES',
)
@click.option(
    '--msg',
    help='текст СМС-сообщения',
    default='Проверка связи',
    envvar='MSG',
)
async def main(login, psw, valid, phones, msg):

    # print(login, psw, valid, phones, msg)

    # отправка СМС
    # send_url = 'https://smsc.ru/rest/send/'
    # # url = 'https://www2.smsc.ru/rest/send/'
    # params = {
    #     'login': login,
    #     'psw': psw,
    #     'valid': valid,
    #     'phones': phones,
    #     'mes': msg,
    #     'cost': 1,  # 1 – получить стоимость рассылки без реальной отправки., 0 (по умолчанию) – обычная отправка.
    #     'fmt': 3,
    #     'op': 1,
    #     'err': 1,
    #     'all': 2,
    # }
    # response = await asks.post(send_url, json=params)
    # print(response.json())
    ## print(response.text)

    # запрос статуса СМС
    status_url = 'https://smsc.ru/rest/status/'
    params = {
        'login': login,
        'psw': psw,
        'phone': phones,
        'id': 104063045,
        'fmt': 3,
        'all': 0,
    }
    response = await asks.post(status_url, json=params)
    print(response.json())


smsc_login: ContextVar[str] = ContextVar('smsc_login')
smsc_password: ContextVar[str] = ContextVar('smsc_password')


async def request_smsc(
        http_method: str,
        api_method: str,
        *,
        login: str,
        password: str,
        payload: dict = {}
) -> dict:
    """Send request to SMSC.ru service.

    Args:
        http_method (str): E.g. 'GET' or 'POST'.
        api_method (str): E.g. 'send' or 'status'.
        login (str): Login for account on smsc.ru.
        password (str): Password for account on smsc.ru.
        payload (dict): Additional request params, override default ones.
    Returns:
        dict: Response from smsc.ru API.
    Raises:
        SmscApiError: If smsc.ru API response status is not 200 or JSON response
        has "error_code" inside.

    Examples:
        # >>> await request_smsc(
        # ...   'POST',
        # ...   'send',
        # ...   login='smsc_login',
        # ...   password='smsc_password',
        # ...   payload={'phones': '+79123456789', 'mes': 'test'}
        # ... )
        {'cnt': 1, 'id': 24}
        # >>> await request_smsc(
        # ...   'POST',
        # ...   'status',
        # ...   login='smsc_login',
        # ...   password='smsc_password',
        # ...   payload={
        # ...     'phone': '+79123456789',
        # ...     'id': '24',
        # ...   }
        # ... )
        {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
    """
    # raise NotImplementedError
    
    payload['login'] = login
    payload['psw'] = password
    payload['fmt'] = 3

    if http_method == 'POST' and api_method == 'send':
        payload['op'] = 1
        payload['err'] = 1
        payload['all'] = 2
        payload['cost'] = 1     # 1 – получить стоимость рассылки без реальной отправки. 3 - отправка, стоимость+баланс
        
        # print(payload)
        response = await asks.post(
            'https://smsc.ru/rest/send/',
            json=payload,
        )
        # print(response.json())
        
        if 'error_code' in response.json():
            raise SmscApiError(f'API error {response.json()}')
        
        return response.json()
    
    elif http_method == 'POST' and api_method == 'status':
        
        # print(payload)
        response = await asks.post(
            'https://smsc.ru/rest/status/',
            json=payload,
        )
        # print(response.json())
        
        if 'error_code' in response.json():
            raise SmscApiError(f'API error {response.json()}')
        return response.json()
        
    else:
        raise SmscApiError(f'API error, http_method: {http_method}, api_method: {api_method}')


async def request_smsc_mock(login, password):
    return await request_smsc('POST', 'send', login=login, password=password)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        env = Env()
        env.read_env()
        # main(_anyio_backend="trio")
        # test do_somthing and request_smsc
        with patch('__main__.request_smsc') as mock_function:
            # mock_function.return_value = {'cnt': 1, 'id': 24}
            mock_function.return_value = {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
            print(trio.run(request_smsc_mock, env('SMSC_LOGIN'), env('SMSC_PASSWORD')))
        