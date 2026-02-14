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
        
        # History stored as raw data objects to allow dynamic formatting
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
                
                # History Sync: Request logic
                if event_type == "history_request" and data.get("from") != self.username:
                    self.send({"type": "history_transfer", "to": data["from"], "content": self.display_history})
                    return

                # History Sync: Transfer logic
                if event_type == "history_transfer" and data.get("to") == self.username:
                    if not self.display_history:
                        self.display_history = data.get("content", [])
                        self._render_batch(self.display_history)
                    return

                sender = data.get("from", "Unknown")
                if sender == self.username:
                    return
                
                # Add raw data to history and print locally
                self._add_to_history(data)
                self._print_line(data)

            def on_sync():
                new_users = set()
                state = self.channel.presence_state()
                for key in state:
                    for presence in state[key]:
                        name = presence.get('user')
                        if name: new_users.add(name)
                
                for user in new_users - self._user_list:
                    if user != self.username:
                        # Request history before the join message to preserve order
                        self.send({"type": "history_request", "content": ""})
                        self._print_line({"from": "System", "content": f"{user} joined the chat"})
                
                for user in self._user_list - new_users:
                    if user != self.username:
                        self._print_line({"from": "System", "content": f"{user} left the chat"})
                
                self._user_list = new_users

            self.channel.on_broadcast("msg", on_msg)
            self.channel.on_presence_sync(on_sync)
            await self.channel.subscribe()
            await self.channel.track({'user': self.username})
            self.enabled = True
            
            # Request history from the room on startup
            self.send({"type": "history_request", "content": ""})

        except Exception:
            self.enabled = False

    def _add_to_history(self, data):
        self.display_history.append(data)
        if len(self.display_history) > 50:
            self.display_history.pop(0)

    def _format_msg(self, data):
        """Dynamically formats the message based on current user."""
        sender = data.get("from", "Unknown")
        msg = data.get("content", "")
        target = data.get("to")
        
        # Identity logic: Change username to [me] if viewing your own message
        is_me = (sender == self.username)
        display_name = "me" if is_me else sender
        
        if sender == "System":
            return f"{Fore.YELLOW}System: {msg}{Style.RESET_ALL}"
        
        color = Fore.GREEN if is_me else self._color_for_user(sender)
        
        if target:
            target_name = "me" if target == self.username else target
            header = f"{color}[{display_name} to {target_name}]{Style.RESET_ALL}"
        else:
            header = f"{color}[{display_name}]{Style.RESET_ALL}"
            
        return f"{header} {msg}"

    def _render_batch(self, history_list):
        with self.terminal_lock:
            sys.stdout.write("\r\033[K")
            for data in history_list:
                formatted = self._format_msg(data)
                sys.stdout.write(f"{formatted}\r\n")
            self.reprint_callback()
            sys.stdout.flush()

    def _print_line(self, data):
        formatted = self._format_msg(data)
        with self.terminal_lock:
            sys.stdout.write(f"\r\033[K{formatted}\r\n")
            self.reprint_callback()
            sys.stdout.flush()

    def _color_for_user(self, name):
        colors = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW, Fore.BLUE]
        return colors[hash(str(name)) % len(colors)]

    def send(self, payload: dict):
        if not self.enabled:
            return
        
        payload["from"] = self.username
        
        # Only add actual chat messages to history (not sync requests)
        if payload.get("type") not in ["history_request", "history_transfer"]:
            self._add_to_history(payload)

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except:
                pass
        asyncio.run_coroutine_threadsafe(_send(), self._loop)