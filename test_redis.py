import redis.asyncio as redis
import asyncio


async def main():
    client = redis.Redis()
    print(f"Ping successful: {await client.ping()}")
    await client.set('phone', '+79615172132')
    print((await client.get('phone')).decode('utf-8'))
    await asyncio.sleep(2)
    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
