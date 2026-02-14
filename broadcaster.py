import asyncio
import threading
import sys
import uuid
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
        
        # History for new joiners
        self.display_history = [] 

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
                event_type = data.get("type", "chat")
                
                # History Sync
                if event_type == "history_request" and data.get("from") != self.username:
                    self.send({"type": "history_transfer", "to": data["from"], "content": self.display_history})
                    return

                if event_type == "history_transfer" and data.get("to") == self.username:
                    if not self.display_history:
                        self.display_history = data.get("content", [])
                        self._render_batch(self.display_history)
                    return

                sender = data.get("from", "Unknown")
                msg = data.get("content", "")
                target = data.get("to")
                
                if sender == self.username:
                    return
                
                color = self._color_for_user(sender)
                if sender == "System":
                    formatted = f"{Fore.YELLOW}System: {msg}{Style.RESET_ALL}"
                elif target:
                    header = f"{color}[{sender} to me]{Style.RESET_ALL}" if target == self.username else f"{color}[{sender} to {target}]{Style.RESET_ALL}"
                    formatted = f"{header} {msg}"
                else:
                    header = f"{color}[{sender}]{Style.RESET_ALL}"
                    formatted = f"{header} {msg}"

                self._add_to_history(formatted)
                self._print_line(formatted)

            def on_sync():
                new_users = set()
                state = self.channel.presence_state()
                for key in state:
                    for presence in state[key]:
                        name = presence.get('user')
                        if name: new_users.add(name)
                
                for user in new_users - self._user_list:
                    if user != self.username:
                        self._print_line(f"{Fore.YELLOW}System: {user} joined the chat{Style.RESET_ALL}")
                
                for user in self._user_list - new_users:
                    if user != self.username:
                        self._print_line(f"{Fore.RED}System: {user} left the chat{Style.RESET_ALL}")
                
                self._user_list = new_users

            self.channel.on_broadcast("msg", on_msg)
            self.channel.on_presence_sync(on_sync)
            await self.channel.subscribe()
            await self.channel.track({'user': self.username})
            self.enabled = True
            
            # Initial history request
            self.send({"type": "history_request", "from": self.username, "content": ""})

        except Exception:
            self.enabled = False

    def _add_to_history(self, text):
        self.display_history.append(text)
        if len(self.display_history) > 50:
            self.display_history.pop(0)

    def _render_batch(self, history_list):
        with self.terminal_lock:
            sys.stdout.write("\r\033[K")
            for msg in history_list:
                sys.stdout.write(f"{msg}\r\n")
            self.reprint_callback()
            sys.stdout.flush()

    def _print_line(self, text):
        with self.terminal_lock:
            sys.stdout.write(f"\r\033[K{text}\r\n")
            self.reprint_callback()
            sys.stdout.flush()

    def _color_for_user(self, name):
        colors = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW, Fore.BLUE]
        return colors[hash(str(name)) % len(colors)]

    def send(self, payload: dict):
        if not self.enabled:
            return
        
        # Ensure 'from' is present for all outgoing payloads
        if "from" not in payload:
            payload["from"] = self.username
            
        if payload.get("type") not in ["history_request", "history_transfer"]:
            # Logic for locally displaying your own message
            target = payload.get("to")
            header = f"{Fore.GREEN}[me to {target}]{Style.RESET_ALL}" if target else f"{Fore.GREEN}[me]{Style.RESET_ALL}"
            self._add_to_history(f"{header} {payload.get('content', '')}")

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except:
                pass
        asyncio.run_coroutine_threadsafe(_send(), self._loop)