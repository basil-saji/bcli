import asyncio
import threading
from supabase import create_async_client
from colorama import Fore, Style, init

init(autoreset=True)


class Broadcaster:
    def __init__(self, url: str, key: str, room: str, username: str):
        self.enabled = False
        self.channel = None
        self.room = room
        self.username = username

        self._loop = asyncio.new_event_loop()
        threading.Thread(
            target=self._run_loop,
            daemon=True
        ).start()

        asyncio.run_coroutine_threadsafe(
            self._init_async(url, key),
            self._loop
        )

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _init_async(self, url: str, key: str):
        try:
            self.client = await create_async_client(url, key)

            # Join if exists, create if not
            self.channel = self.client.channel(f"room_{self.room}")

            # RECEIVE messages
            def on_msg(payload):
                data = payload["payload"]
                sender = data["from"]
                msg = data["content"]

                # Ignore our own messages (prevents duplicate)
                if sender == self.username:
                    return

                color = self._color_for_user(sender)

                print(f"\n{color}[{sender}]{Style.RESET_ALL} {msg}")
                print("> ", end="", flush=True)

            self.channel.on_broadcast("msg", on_msg)

            await self.channel.subscribe()

            self.enabled = True
            print(f"Connected to room_{self.room}")

        except Exception as e:
            print(f"Init failed: {e}")
            self.enabled = False
            self.channel = None

    def _color_for_user(self, name):
        colors = [
            Fore.CYAN,
            Fore.MAGENTA,
            Fore.YELLOW,
            Fore.BLUE
        ]
        return colors[hash(name) % len(colors)]

    def send(self, payload: dict):
        if not self.enabled or self.channel is None:
            return

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except Exception as e:
                print(f"Send error: {e}")

        asyncio.run_coroutine_threadsafe(_send(), self._loop)
