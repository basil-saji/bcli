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
        
        # History stores dictionaries for structured transfer: {"from": sender, "to": target, "content": msg, "type": type}
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
                msg_type = data.get("type", "chat")
                
                if sender == self.username:
                    return
                
                # Add to history as structured data
                self._add_to_history(sender, target, msg, msg_type)
                
                # Format for display
                formatted = self._format_msg(sender, target, msg, msg_type)
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
            self.send({"type": "history_request", "from": self.username, "content": ""})

        except Exception:
            self.enabled = False

    def _format_msg(self, sender, target, content, msg_type="chat"):
        if sender == "System":
            return f"{Fore.YELLOW}System: {content}{Style.RESET_ALL}"
        
        is_me = (sender == self.username)
        color = Fore.GREEN if is_me else self._color_for_user(sender)
        display_name = "me" if is_me else sender

        # Special formatting for files
        if msg_type == "file":
            header = f"{Fore.YELLOW}[{display_name} shared a file]{Style.RESET_ALL}"
            return f"{header}\r\n{content}"

        if target:
            target_display = "me" if target == self.username else target
            header = f"{color}[{display_name} to {target_display}]{Style.RESET_ALL}"
        else:
            header = f"{color}[{display_name}]{Style.RESET_ALL}"
            
        return f"{header} {content}"

    def _add_to_history(self, sender, target, content, msg_type="chat"):
        self.display_history.append({"from": sender, "to": target, "content": content, "type": msg_type})
        if len(self.display_history) > 50:
            self.display_history.pop(0)

    def _render_batch(self, history_list):
        with self.terminal_lock:
            sys.stdout.write("\r\033[K")
            for msg_data in history_list:
                formatted = self._format_msg(msg_data["from"], msg_data["to"], msg_data["content"], msg_data.get("type", "chat"))
                sys.stdout.write(f"{formatted}\r\n")
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
        
        if "from" not in payload:
            payload["from"] = self.username
            
        if payload.get("type") not in ["history_request", "history_transfer"]:
            sender = payload["from"]
            target = payload.get("to")
            content = payload.get('content', '')
            msg_type = payload.get('type', 'chat')
            
            # Add structured data to history
            self._add_to_history(sender, target, content, msg_type)

        async def _send():
            try:
                await self.channel.send_broadcast("msg", payload)
            except:
                pass
        asyncio.run_coroutine_threadsafe(_send(), self._loop)