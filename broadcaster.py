import asyncio
import threading
from supabase import create_async_client


class Broadcaster:
    def __init__(self, url: str, key: str, room: str):
        self.enabled = False
        self.channel = None
        self.room = room

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

            # This joins if exists, creates if not
            self.channel = self.client.channel(f"room_{self.room}")

            # RECEIVE messages
            self.channel.on_broadcast(
                "msg",
                lambda payload: print(
                    f"\n[{payload['payload']['from']}] {payload['payload']['content']}"
                )
            )

            await self.channel.subscribe()

            self.enabled = True
            print(f"Connected to room_{self.room}")

        except Exception as e:
            print(f"Init failed: {e}")
            self.enabled = False
            self.channel = None

    def send(self, payload: dict):
        if not self.enabled or self.channel is None:
            return

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except Exception as e:
                print(f"Send error: {e}")

        asyncio.run_coroutine_threadsafe(_send(), self._loop)
