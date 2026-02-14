import asyncio
import threading
import sys
from supabase import create_async_client
from colorama import Fore, Style, init

init(autoreset=True)

class Broadcaster:
    def __init__(self, url: str, key: str, room: str, username: str, terminal_lock, reprint_callback):
        self.enabled = False
        self.channel = None
        self.room = room
        self.username = username
        self.terminal_lock = terminal_lock
        self.reprint_callback = reprint_callback
        self._user_list = set()

        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self._init_async(url, key), self._loop)

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
                target = data.get("to") # Get the recipient if exists
                
                if sender == self.username: return
                
                if sender == "System":
                    self._print_system_line(f"{Fore.YELLOW}System: {msg}{Style.RESET_ALL}")
                else:
                    color = self._color_for_user(sender)
                    # TAGGING LOGIC
                    if target:
                        if target == self.username:
                            header = f"{color}[{sender} to me]{Style.RESET_ALL}"
                        else:
                            header = f"{color}[{sender} to {target}]{Style.RESET_ALL}"
                    else:
                        header = f"{color}[{sender}]{Style.RESET_ALL}"
                        
                    self._print_system_line(f"{header} {msg}")

            def on_sync():
                new_users = set()
                state = self.channel.presence_state()
                for key in state:
                    for presence in state[key]:
                        name = presence.get('user')
                        if name: new_users.add(name)

                for user in new_users - self._user_list:
                    if user != self.username:
                        self._print_system_line(f"{Fore.YELLOW}System: {user} joined the chat{Style.RESET_ALL}")
                
                for user in self._user_list - new_users:
                    if user != self.username:
                        self._print_system_line(f"{Fore.RED}System: {user} left the chat{Style.RESET_ALL}")
                
                self._user_list = new_users

            self.channel.on_broadcast("msg", on_msg)
            self.channel.on_presence_sync(on_sync)
            
            await self.channel.subscribe()
            await self.channel.track({'user': self.username})
            self.enabled = True
        except Exception:
            self.enabled = False

    def get_active_users(self):
        return sorted(list(self._user_list))

    def _print_system_line(self, text):
        with self.terminal_lock:
            sys.stdout.write(f"\r\033[K{text}\n")
            self.reprint_callback()
            sys.stdout.flush()

    def _color_for_user(self, name):
        colors = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW, Fore.BLUE]
        return colors[hash(name) % len(colors)]

    def send(self, payload: dict):
        if not self.enabled or self.channel is None: return
        async def _send():
            try: await self.channel.send_broadcast("msg", payload)
            except Exception: pass
        asyncio.run_coroutine_threadsafe(_send(), self._loop)