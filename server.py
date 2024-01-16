import asyncio
import trio

from typing import AsyncGenerator
from quart import Quart, render_template, websocket
from quart_trio import QuartTrio


class Broker:
    def __init__(self) -> None:
        self.connections = set()

    async def publish(self, message: str) -> None:
        for connection in self.connections:
            await connection.put(message)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        connection = asyncio.Queue()
        self.connections.add(connection)
        try:
            while True:
                yield await connection.get()
        finally:
            self.connections.remove(connection)


app = Quart(__name__)
# app = QuartTrio(__name__)
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
    # try:
    #     async with trio.open_nursery() as nursery:
    #         nursery.start_soon(_receive)
    #     async for message in broker.subscribe():
    #         await websocket.send(message)
    
    # except BaseException as e:
    #     print(f'websocket funcs crashed with exception: {e}')


if __name__ == "__main__":
    app.run(debug=True)
