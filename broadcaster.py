import asyncio
import threading
import sys
import uuid
import os
import base64
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
        self._chunks = {} 

        self.download_dir = "downloads"
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

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
                target = data.get("to")
                msg_type = data.get("type", "chat")
                filename = data.get("filename")
                is_binary = data.get("is_binary", False)

                msg_id = data.get("msg_id")
                if msg_id:
                    chunk_idx = data.get("chunk_idx")
                    total_chunks = data.get("total_chunks", 1)
                    if msg_id not in self._chunks:
                        self._chunks[msg_id] = [None] * total_chunks
                    self._chunks[msg_id][chunk_idx] = data.get("content", "")
                    
                    if None not in self._chunks[msg_id]:
                        full_content = "".join(self._chunks[msg_id])
                        del self._chunks[msg_id]
                        if sender != self.username:
                            if msg_type == "file" and filename:
                                self._save_file(filename, full_content, is_binary)
                            self._add_to_history(sender, target, full_content, msg_type, filename, is_binary)
                            formatted = self._format_msg(sender, target, full_content, msg_type, filename, is_binary)
                            self._print_line(formatted)
                    return

                if sender == self.username: return
                msg = data.get("content", "")
                self._add_to_history(sender, target, msg, msg_type, filename, is_binary)
                formatted = self._format_msg(sender, target, msg, msg_type, filename, is_binary)
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

    def get_users(self):
        """Public accessor for the active user list."""
        return sorted(list(self._user_list))

    def _save_file(self, filename, content, is_binary=False):
        try:
            path = os.path.join(self.download_dir, filename)
            if is_binary:
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(content))
            else:
                with open(path, 'w') as f:
                    f.write(content)
            self._print_line(f"{Fore.CYAN}System: Received file saved to {path}{Style.RESET_ALL}")
        except Exception as e:
            self._print_line(f"{Fore.RED}System: Failed to save file {filename}: {e}{Style.RESET_ALL}")

    def _format_msg(self, sender, target, content, msg_type="chat", filename=None, is_binary=False):
        if not is_binary: content = content.replace('\n', '\r\n')
        if sender == "System": return f"{Fore.YELLOW}System: {content}{Style.RESET_ALL}"
        is_me = (sender == self.username)
        color = Fore.GREEN if is_me else self._color_for_user(sender)
        display_name = "me" if is_me else sender
        if msg_type == "file":
            fname = filename or "file"
            header = f"{Fore.YELLOW}[{display_name} shared a file: {fname}]{Style.RESET_ALL}"
            prompt = f"use \";show {fname}\" to view, \";open {fname}\" to open, \";copy {fname}\" to copy"
            return f"{header} {prompt}"
        if target:
            t_display = "me" if target == self.username else target
            header = f"{color}[{display_name} to {t_display}]{Style.RESET_ALL}"
        else:
            header = f"{color}[{display_name}]{Style.RESET_ALL}"
        return f"{header} {content}"

    def _add_to_history(self, sender, target, content, msg_type="chat", filename=None, is_binary=False):
        self.display_history.append({"from": sender, "to": target, "content": content, "type": msg_type, "filename": filename, "is_binary": is_binary})
        if len(self.display_history) > 50: self.display_history.pop(0)

    def _render_batch(self, history_list):
        with self.terminal_lock:
            sys.stdout.write("\r\033[K")
            for m in history_list:
                formatted = self._format_msg(m["from"], m["to"], m["content"], m.get("type", "chat"), m.get("filename"), m.get("is_binary", False))
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
        if not self.enabled: return
        if "from" not in payload: payload["from"] = self.username
        content = payload.get("content", "")
        chunk_size = 100 * 1024 
        msg_id = str(uuid.uuid4())
        
        if payload.get("type") not in ["history_request", "history_transfer"] and content:
            chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
            total = len(chunks)
            self._add_to_history(payload["from"], payload.get("to"), content, payload.get('type', 'chat'), payload.get('filename'), payload.get('is_binary', False))
            async def _send_chunks():
                for idx, chunk in enumerate(chunks):
                    cp = payload.copy()
                    cp.update({"content": chunk, "msg_id": msg_id, "chunk_idx": idx, "total_chunks": total})
                    try: await self.channel.send_broadcast("msg", cp)
                    except: pass
            asyncio.run_coroutine_threadsafe(_send_chunks(), self._loop)
        else:
            async def _send_single():
                try: await self.channel.send_broadcast("msg", payload)
                except: pass
            asyncio.run_coroutine_threadsafe(_send_single(), self._loop)