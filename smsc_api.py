import asks
import asyncclick as click

from environs import Env
from contextlib import suppress


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

    url = 'https://smsc.ru/rest/send/'
    # url = 'https://www2.smsc.ru/rest/send/'
    params = {
        'login': login,
        'psw': psw,
        'valid': valid,
        'phones': phones,
        'mes': msg,
        'cost': 1,  # 1 – получить стоимость рассылки без реальной отправки., 0 (по умолчанию) – обычная отправка.
        'fmt': 3,
    }

    # print(params)

    response = await asks.post(url, json=params)
    print(response.json())


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        env = Env()
        env.read_env()
        main(_anyio_backend="trio")
