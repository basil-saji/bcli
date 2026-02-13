import asyncio
import uuid
from rtc import init_rtc, channel
from config import USERNAME

def on_message(payload):
    data = payload["payload"]
    sender = data["from"]
    msg = data["content"]

    print(f"\n[{sender}] {msg}")

async def main():
    await init_rtc(on_message)

    print("Connected. Start typing...\n")

    while True:
        text = input("> ")

        payload = {
            "id": str(uuid.uuid4()),
            "from": USERNAME,
            "content": text
        }

        await channel.send({
            "type": "broadcast",
            "event": "msg",
            "payload": payload
        })

        print(f"[me] {text}")

asyncio.run(main())
