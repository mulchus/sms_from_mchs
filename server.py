import trio
import json
import smsc_api

from quart import render_template, websocket, request
from quart_trio import QuartTrio
from mock import patch
from environs import Env
from pydantic import BaseModel, constr, ValidationError


app = QuartTrio(__name__)


class Message(BaseModel):
    text: constr(pattern=r'^[a-zA-Zа-яА-Я0-9_.,!+-]')


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
            # mock_function.return_value = {'cnt': 1, 'id': 24}
            mock_function.return_value = {'status': 1, 'last_date': '28.12.2019 19:20:22', 'last_timestamp': 1577550022}
            print(await smsc_api.request_smsc_mock(env('SMSC_LOGIN'), env('SMSC_PASSWORD')))
        print(f'Сообщение с текстом {form["text"]} отправлено')
        return json.dumps(form['text'])
    else:
        return await render_template('index.html')


@app.get("/")
async def index():
    return await render_template("index.html")


async def receive():
    while True:
        for num in range(100):
            data = {
                "msgType": "SMSMailingStatus",
                "SMSMailings": [
                    {
                        "timestamp": 1123131392.734,
                        "SMSText": "Сегодня гроза! Будьте осторожны!",
                        "mailingId": "1",
                        "totalSMSAmount": 100,
                        "deliveredSMSAmount": num,
                        "failedSMSAmount": 0,
                    },
                ]
            }
            await websocket.send_json(data)
            await trio.sleep(1)


@app.websocket('/ws')
async def ws():
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(receive)
    except BaseException as e:
        print(f'websocket funcs crashed with exception: {e}')


if __name__ == "__main__":
    env = Env()
    env.read_env()
    app.run()
