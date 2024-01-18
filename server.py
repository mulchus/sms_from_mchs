import trio

from quart import render_template, websocket
from quart_trio import QuartTrio

app = QuartTrio(__name__)


@app.get("/")
async def index():
    return await render_template("index.html")


async def receive():
    while True:
        await websocket.send(f'Received: {await websocket.receive()}')


@app.websocket('/ws')
async def ws():
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(receive)
   
    except BaseException as e:
        print(f'websocket funcs crashed with exception: {e}')


if __name__ == "__main__":
    app.run()
