import asyncio

# from quart_trio import QuartTrio

from quart import Quart, render_template, websocket

from broker import Broker

app = Quart(__name__)
broker = Broker()


@app.get("/")
async def index():
    return await render_template("index.html")


async def _receive() -> None:
    while True:
        message = await websocket.receive()
        await broker.publish(f'Received: echo {message}')


@app.websocket("/ws")
async def ws() -> None:
    try:
        task = asyncio.ensure_future(_receive())
        async for message in broker.subscribe():
            await websocket.send(message)
    finally:
        task.cancel()
        await task


# def run():
app.run(debug=True)
