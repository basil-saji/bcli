import sys, time, threading, json, os
from broadcaster import Broadcaster
from colorama import Fore, Style, init

try:
    import msvcrt
    def get_key(): return msvcrt.getch().decode('utf-8', errors='ignore')
except ImportError:
    import tty, termios
    def get_key():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

init(autoreset=True)
MEMORY_FILE = "memory.json"
#
SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"

def load_mem():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_mem(data):
    with open(MEMORY_FILE, 'w') as f: json.dump(data, f)

def run_cli():
    mem = load_mem()
    room = input("Room id: ").strip() or "general"
    
    username = mem.get("username")
    if not username:
        username = input("Username: ").strip() or f"user_{int(time.time()) % 1000}"
        save_mem({"username": username})
    else:
        print(f"Welcome back, {username}!")

    input_buffer = ""
    terminal_lock = threading.Lock()
    # State tracking for multiline code mode
    code_mode = False
    code_lines = []

    def reprint_input():
        prompt = "CODE> " if code_mode else "> "
        sys.stdout.write(f"\r\033[K{prompt}{input_buffer}")
        sys.stdout.flush()

    bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username, terminal_lock, reprint_input)

    print(f"{Fore.YELLOW}Connecting...{Style.RESET_ALL}", end="\r")
    while not bc.enabled: 
        time.sleep(0.1)
    
    sys.stdout.write("\r\033[K")
    sys.stdout.write(f"{Fore.GREEN}Connected to room {room}{Style.RESET_ALL}\r\n")

    reprint_input()

    try:
        while True:
            char = get_key()
            if char == '\x03': 
                raise KeyboardInterrupt

            with terminal_lock:
                if char in ('\r', '\n'):
                    sys.stdout.write("\r\033[K")
                    
                    # Handle Multiline Code Mode logic
                    if code_mode:
                        if input_buffer.strip().upper() == "END":
                            code_mode = False
                            full_code = "\n".join(code_lines)
                            sys.stdout.write(f"{Fore.GREEN}[me code]{Style.RESET_ALL}\r\n{full_code}\r\n")
                            bc.send({"content": full_code, "type": "chat"})
                            code_lines = []
                        else:
                            code_lines.append(input_buffer)
                            sys.stdout.write(f"  {input_buffer}\r\n")
                        input_buffer = ""
                        reprint_input()
                        continue

                    # Standard Command Handling
                    if input_buffer.startswith(';@'):
                        parts = input_buffer[2:].split(' ', 1)
                        if len(parts) == 2:
                            sys.stdout.write(f"{Fore.GREEN}[me to {parts[0]}]{Style.RESET_ALL} {parts[1]}\r\n")
                            bc.send({"to": parts[0], "content": parts[1]})
                        input_buffer = ""

                    elif input_buffer.startswith(';'):
                        parts = input_buffer[1:].split()
                        cmd = parts[0].lower() if parts else ""
                        
                        if cmd == "code":
                            code_mode = True
                            sys.stdout.write(f"{Fore.YELLOW}--- Multiline Mode (Type 'END' to send) ---\r\n{Style.RESET_ALL}")
                        
                        elif cmd == "send" and len(parts) > 1:
                            filepath = parts[1]
                            if os.path.exists(filepath):
                                try:
                                    with open(filepath, 'r') as f:
                                        content = f.read()
                                    sys.stdout.write(f"{Fore.GREEN}[me shared {filepath}]{Style.RESET_ALL}\r\n")
                                    bc.send({"content": content, "type": "file"})
                                except Exception as e:
                                    sys.stdout.write(f"{Fore.RED}Error reading file: {e}\r\n")
                            else:
                                sys.stdout.write(f"{Fore.RED}File not found: {filepath}\r\n")

                        elif cmd == "help":
                            sys.stdout.write(f"{Fore.CYAN}--- Available Commands ---\r\n")
                            sys.stdout.write(f";help           - Show help\r\n")
                            sys.stdout.write(f";code           - Multiline mode\r\n")
                            sys.stdout.write(f";send [file]    - Share file contents\r\n")
                            sys.stdout.write(f";all            - List users\r\n")
                            sys.stdout.write(f";@[user] [msg]  - Tag user\r\n")
                            sys.stdout.write(f";nick [name]    - Change name\r\n")
                            sys.stdout.write(f";clear          - Clear screen\r\n")
                            sys.stdout.write(f";exit/quit/kill - Exit{Style.RESET_ALL}\r\n")
                        
                        elif cmd == "all":
                            users = sorted(list(bc._user_list))
                            sys.stdout.write(f"{Fore.CYAN}Online: {', '.join(users) if users else 'none'}\r\n")

                        elif cmd == "clear": 
                            sys.stdout.write("\033[H\033[J")
                        elif cmd in ("exit", "quit", "kill"): 
                            raise KeyboardInterrupt
                        elif cmd == "nick" and len(parts) > 1:
                            old = bc.username
                            bc.username = parts[1]
                            save_mem({"username": bc.username})
                            sys.stdout.write(f"{Fore.YELLOW}System: Name is now {bc.username}\r\n")
                            bc.send({"from": "System", "content": f"{old} changed their name to {bc.username}"})
                        
                        input_buffer = ""
                    
                    elif input_buffer.strip():
                        # Standard immediate local display
                        sys.stdout.write(f"{Fore.GREEN}[me]{Style.RESET_ALL} {input_buffer}\r\n")
                        bc.send({"content": input_buffer})
                        input_buffer = ""
                    
                    reprint_input()

                elif char in ('\x7f', '\x08'):
                    if len(input_buffer) > 0:
                        input_buffer = input_buffer[:-1]
                        reprint_input()
                elif ord(char) >= 32:
                    input_buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write(f"\r\033[K\r\n{Fore.RED}Exiting...{Style.RESET_ALL}\r\n")
        sys.exit(0)

if __name__ == "__main__":
    run_cli()