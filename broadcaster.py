import asyncio
import threading
import sys
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

        self.init_task = asyncio.run_coroutine_threadsafe(
            self._init_async(url, key),
            self._loop
        )

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _init_async(self, url: str, key: str):
        try:
            self.client = await create_async_client(url, key)
            self.channel = self.client.channel(f"room_{self.room}")

            def on_msg(payload):
                data = payload["payload"]
                sender = data["from"]
                msg = data["content"]

                if sender == self.username:
                    return

                color = self._color_for_user(sender)
                
                # UI FIX: \r moves to start, \033[K clears the current prompt line
                # We only append "> " at the end to restore the line for the user
                sys.stdout.write(f"\r\033[K{color}[{sender}]{Style.RESET_ALL} {msg}\n> ")
                sys.stdout.flush()

            self.channel.on_broadcast("msg", on_msg)
            await self.channel.subscribe()
            self.enabled = True

        except Exception as e:
            self.enabled = False

    def _color_for_user(self, name):
        colors = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW, Fore.BLUE]
        return colors[hash(name) % len(colors)]

    def send(self, payload: dict):
        if not self.enabled or self.channel is None:
            return

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except Exception:
                pass

        asyncio.run_coroutine_threadsafe(_send(), self._loop)