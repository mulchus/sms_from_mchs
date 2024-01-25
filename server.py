import trio
import asyncio
import trio_asyncio
import json
import smsc_api
import argparse

from quart import render_template, websocket, request
from quart_trio import QuartTrio
from mock import patch
from environs import Env
from pydantic import BaseModel, constr, ValidationError
from hypercorn.trio import serve
from hypercorn.config import Config as HyperConfig
from redis import asyncio as aioredis
from db import Database


app = QuartTrio(__name__)


class Message(BaseModel):
    text: constr(pattern=r'^[a-zA-Zа-яА-Я0-9_.,!+-]')


def create_argparser():
    parser = argparse.ArgumentParser(description='Redis database usage example')
    parser.add_argument(
        '--address',
        action='store',
        dest='redis_uri',
        help='Redis URL. See examples at '
             'https://aioredis.readthedocs.io/en/latest/api/high-level/#aioredis.client.Redis.from_url',
        default='redis://localhost'
    )
    return parser


@app.route("/send/", methods=["GET", "POST"])
async def create():
    if request.method == "POST":
        form = await request.form
        try:
            Message(text=form['text'])  # валидация сообщения при помощи pydantic
        except ValidationError as e:
            return json.dumps({'errorMessage': e.errors()[0]['msg']})
        # здесь закомментирована реальная отправка и проверка статуса
        # send_ressponce = await smsc_api.request_smsc(
        #     http_method='POST',
        #     api_method='send',
        #     login=env('SMSC_LOGIN'),
        #     password=env('SMSC_PASSWORD'),
        #     payload={'phones': env('PHONES'), 'mes': form['text']}
        # )
        # print(send_ressponce)
        # for phone in env('PHONES').split(','):
        #     status_ressponce = await smsc_api.request_smsc(
        #         http_method='POST',
        #         api_method='status',
        #         login=env('SMSC_LOGIN'),
        #         password=env('SMSC_PASSWORD'),
        #         payload={'phone': phone, 'id': send_ressponce['id']}
        #     )
        #     print(status_ressponce)
        with patch('smsc_api.request_smsc') as mock_function:
            mock_function.return_value = {'cnt': 1, 'id': 24}
            # mock_function.return_value = {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
            sms_id = (await smsc_api.request_smsc_mock(env('SMSC_LOGIN'), env('SMSC_PASSWORD')))['id']
        print(f'sms_id {sms_id}')
        print(f'Сообщение с текстом {form["text"]} отправлено')

        sms_id = '99'

        phones = [
            '+7 999 519 05 57',
            '911',
            '112',
        ]
        text = 'Вечером будет шторм!'

        await trio_asyncio.aio_as_trio(db.add_sms_mailing)(sms_id, phones, text)

        sms_ids = await trio_asyncio.aio_as_trio(db.list_sms_mailings())
        print('Registered mailings ids', sms_ids)

        pending_sms_list = await trio_asyncio.aio_as_trio(db.get_pending_sms_list())
        print('pending:')
        print(pending_sms_list)

        await trio_asyncio.aio_as_trio(db.update_sms_status_in_bulk([
            # [sms_id, phone_number, status]
            [sms_id, '112', 'failed'],
            [sms_id, '911', 'pending'],
            [sms_id, '+7 999 519 05 57', 'delivered'],
            # following statuses are available: failed, pending, delivered
        ]))

        pending_sms_list = await trio_asyncio.aio_as_trio(db.get_pending_sms_list())
        print('pending:')
        print(pending_sms_list)

        sms_mailings = await trio_asyncio.aio_as_trio(db.get_sms_mailings(sms_id))
        print('sms_mailings')
        print(sms_mailings)

        return json.dumps(form['text'])
    else:
        return await render_template('index.html')


@app.get("/")
async def index():
    return await render_template("index.html")


# отправка фронтэнду информации о сообщении и статусе (тест в цикле)
async def receive():
    while True:
        await trio.sleep(1)
    #     for num in range(100):
    #         data = {
    #             "msgType": "SMSMailingStatus",
    #             "SMSMailings": [
    #                 {
    #                     "timestamp": 1123131392.734,
    #                     "SMSText": "Сегодня гроза! Будьте осторожны!",
    #                     "mailingId": "1",
    #                     "totalSMSAmount": 100,
    #                     "deliveredSMSAmount": num,
    #                     "failedSMSAmount": 0,
    #                 },
    #             ]
    #         }
    #         await websocket.send_json(data)
    #         await trio.sleep(1)


@app.websocket('/ws')
async def ws():
    try:
        async with trio.open_nursery() as nursery:
            # pass
            # nursery.start_soon()
            nursery.start_soon(receive)
    except BaseException as e:
        print(f'websocket funcs crashed with exception: {e}')


async def run_server():
    async with trio_asyncio.open_loop() as loop:
        config = HyperConfig()
        config.bind = [f"127.0.0.1:5000"]
        config.use_reloader = True

        # здесь живёт остальной код инициализации
        # ...
        await serve(app, config)


if __name__ == "__main__":
    env = Env()
    env.read_env()
    parser = create_argparser()
    args = parser.parse_args()
    redis = aioredis.from_url(args.redis_uri, decode_responses=True)
    db = Database(redis)
    # app.run()
    trio_asyncio.run(run_server)
