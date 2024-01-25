import trio
import trio_asyncio
import argparse

from redis import asyncio as aioredis
from db import Database


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


async def main():
    async with trio_asyncio.open_loop():
        parser = create_argparser()
        args = parser.parse_args()

        redis = aioredis.from_url(args.redis_uri, decode_responses=True)

        try:
            db = Database(redis)

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

            async def send():
                while True:
                    await trio.sleep(1)
                    await trio_asyncio.aio_as_trio(redis.publish)('updates', sms_id)

            async def listen():
                channel = redis.pubsub()
                await trio_asyncio.aio_as_trio(channel.subscribe)('updates')

                while True:
                    message = await trio_asyncio.aio_as_trio(channel.get_message)(ignore_subscribe_messages=True,
                                                                                  timeout=1.0)
                    if not message:
                        continue
                    print('Got message:', repr(message['data']))

            async with trio.open_nursery() as nursery:
                nursery.start_soon(send)
                nursery.start_soon(listen)

        finally:
            await trio_asyncio.aio_as_trio(redis.close)()


if __name__ == '__main__':
    trio_asyncio.run(main)
    