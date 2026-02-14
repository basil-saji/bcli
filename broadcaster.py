import asyncio
import threading
import sys
import uuid
import json
import os
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
        
        self.display_history = [] 
        self.my_msg_ids = []

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
                
                if event_type == "history_request" and data["from"] != self.username:
                    self.send({"type": "history_transfer", "to": data["from"], "content": self.display_history})
                    return

                if event_type == "history_transfer" and data.get("to") == self.username:
                    if not self.display_history:
                        self.display_history = data["content"]
                        self._refresh_ui()
                    return

                if event_type == "delete":
                    target_id = data.get("target_id")
                    self.display_history = [m for m in self.display_history if m['id'] != target_id]
                    self._refresh_ui()
                    return

                sender = data.get("from", "Unknown")
                msg = data.get("content", "")
                target = data.get("to")
                if sender == self.username: return
                
                color = self._color_for_user(sender)
                if sender == "System":
                    formatted = f"{Fore.YELLOW}System: {msg}{Style.RESET_ALL}"
                elif target:
                    header = f"{color}[{sender} to me]{Style.RESET_ALL}" if target == self.username else f"{color}[{sender} to {target}]{Style.RESET_ALL}"
                    formatted = f"{header} {msg}"
                else:
                    formatted = f"{color}[{sender}]{Style.RESET_ALL} {msg}"

                self._add_to_history(data.get("id"), formatted)
                self._refresh_ui()

            def on_sync():
                new_users = set()
                state = self.channel.presence_state()
                for key in state:
                    for presence in state[key]:
                        name = presence.get('user')
                        if name: new_users.add(name)
                
                for user in new_users - self._user_list:
                    if user != self.username:
                        self._add_to_history(None, f"{Fore.YELLOW}System: {user} joined the chat{Style.RESET_ALL}")
                for user in self._user_list - new_users:
                    if user != self.username:
                        self._add_to_history(None, f"{Fore.RED}System: {user} left the chat{Style.RESET_ALL}")
                
                self._user_list = new_users
                self._refresh_ui()

            self.channel.on_broadcast("msg", on_msg)
            self.channel.on_presence_sync(on_sync)
            await self.channel.subscribe()
            await self.channel.track({'user': self.username})
            self.enabled = True
            
            # Request history from others
            self.send({"type": "history_request", "content": ""})

        except Exception as e:
            self.enabled = False

    def _add_to_history(self, msg_id, formatted_text):
        self.display_history.append({"id": msg_id, "text": formatted_text})
        if len(self.display_history) > 50: self.display_history.pop(0)

    def _refresh_ui(self):
        with self.terminal_lock:
            sys.stdout.write("\033[H\033[J") 
            print(f"{Fore.CYAN}Room: {self.room}{Style.RESET_ALL} | {Fore.GREEN}User: {self.username}{Style.RESET_ALL}\n")
            for entry in self.display_history:
                print(entry["text"])
            self.reprint_callback()
            sys.stdout.flush()

    def send(self, payload: dict):
        if not self.enabled or self.channel is None: return
        
        # Ensure 'from' is always set before sending
        payload["from"] = self.username
        msg_id = str(uuid.uuid4())
        payload["id"] = msg_id
        
        if payload.get("type") not in ["delete", "history_request", "history_transfer"]:
            self.my_msg_ids.insert(0, msg_id)
            target = payload.get("to")
            header = f"{Fore.GREEN}[me to {target}]{Style.RESET_ALL}" if target else f"{Fore.GREEN}[me]{Style.RESET_ALL}"
            self._add_to_history(msg_id, f"{header} {payload.get('content', '')}")

        async def _send():
            try: 
                await self.channel.send_broadcast("msg", payload)
            except: 
                pass
        
        asyncio.run_coroutine_threadsafe(_send(), self._loop)
        self._refresh_ui()

    def _color_for_user(self, name):
        colors = [Fore.CYAN, Fore.MAGENTA, Fore.YELLOW, Fore.BLUE]
        return colors[hash(str(name)) % len(colors)]