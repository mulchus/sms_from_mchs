import trio
import trio_asyncio
import json
import smsc_api
import argparse

from quart import render_template, websocket, request
from quart_trio import QuartTrio
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
    _parser = argparse.ArgumentParser(description='Redis database usage example')
    _parser.add_argument(
        '--address',
        action='store',
        dest='redis_uri',
        help='Redis URL. See examples at '
             'https://aioredis.readthedocs.io/en/latest/api/high-level/#aioredis.client.Redis.from_url',
        default='redis://localhost'
    )
    return _parser


@app.route("/send/", methods=["GET", "POST"])
async def create():
    if request.method == "POST":
        form = await request.form
        try:
            Message(text=form['text'])  # валидация сообщения при помощи pydantic
        except ValidationError as e:
            return json.dumps({'errorMessage': e.errors()[0]['msg']})
        
        # реальная отправка
        send_ressponce = await smsc_api.request_smsc(
            http_method='POST',
            api_method='send',
            login=env('SMSC_LOGIN'),
            password=env('SMSC_PASSWORD'),
            payload={'phones': env('PHONES'), 'mes': form['text']}
        )
        # print(send_ressponce)
        
        # если в настройках cost = 1 (стоимость рассылки без реальной отправки), то в ответе не будет id
        if 'id' in send_ressponce:
            sms_id = str(send_ressponce['id'])
        else:
            sms_id = '104063047'   # последнее известное реальное id
        
        # сохранение в базу данных
        phones = env('PHONES').split(',')
        text = form['text']
        await trio_asyncio.aio_as_trio(db.add_sms_mailing)(sms_id, phones, text)
        
        # проверка статуса
        for phone in env('PHONES').split(','):
            status_ressponce = await smsc_api.request_smsc(
                http_method='POST',
                api_method='status',
                login=env('SMSC_LOGIN'),
                password=env('SMSC_PASSWORD'),
                payload={'phone': phone, 'id': sms_id}
            )
            # print(status_ressponce)

        return json.dumps(form['text'])
    else:
        return await render_template('index.html')


@app.get("/")
async def index():
    return await render_template("index.html")


# отправка фронтэнду информации о сообщении и статусе (тест в цикле)
async def receive():
    while True:
        sms_mailings = []
        sms_ids = await trio_asyncio.aio_as_trio(db.list_sms_mailings())
        for sms_id in sms_ids:
            sms_mailing = (await trio_asyncio.aio_as_trio(db.get_sms_mailings(sms_id)))[0]
            sms_mailings.append(
                {
                    "timestamp": sms_mailing['created_at'],
                    "SMSText": sms_mailing['text'],
                    "mailingId": sms_mailing['sms_id'],
                    "totalSMSAmount": 100,
                    "deliveredSMSAmount": 0,
                    "failedSMSAmount": 0,
                }
            )
        all_sms_info = {"msgType": "SMSMailingStatus", "SMSMailings": sms_mailings}
        await websocket.send_json(all_sms_info)
        await trio.sleep(1)


@app.websocket('/ws')
async def ws():
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(receive)
    except BaseException as e:
        print(f'websocket funcs crashed with exception: {e}')


async def run_server():
    async with trio_asyncio.open_loop():
        config = HyperConfig()
        config.bind = [f"127.0.0.1:5000"]
        config.use_reloader = True

        await serve(app, config)


if __name__ == "__main__":
    env = Env()
    env.read_env()
    parser = create_argparser()
    args = parser.parse_args()
    redis = aioredis.from_url(args.redis_uri, decode_responses=True)
    db = Database(redis)
    trio_asyncio.run(run_server)
