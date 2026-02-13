from rtc import channel
from config import USERNAME
import uuid

print("Connected. Type messages.\n")

while True:
    text = input("> ")

    payload = {
        "id": str(uuid.uuid4()),
        "from": USERNAME,
        "content": text
    }

    channel.send({
        "type": "broadcast",
        "event": "msg",
        "payload": payload
    })

    print(f"[me] {text}")
