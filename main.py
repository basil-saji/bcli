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

    def reprint_input():
        sys.stdout.write(f"\r\033[K> {input_buffer}")
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
                    
                    if input_buffer.startswith(';@'):
                        parts = input_buffer[2:].split(' ', 1)
                        if len(parts) == 2:
                            # Local display logic handled by bc._print_line
                            bc.send({"to": parts[0], "content": parts[1]})
                            bc._print_line({"from": bc.username, "to": parts[0], "content": parts[1]})
                        input_buffer = ""

                    elif input_buffer.startswith(';'):
                        parts = input_buffer[1:].split()
                        cmd = parts[0].lower() if parts else ""
                        
                        if cmd == "help":
                            sys.stdout.write(f"{Fore.CYAN}--- Commands ---\r\n")
                            sys.stdout.write(f";all, ;nick [name], ;clear, ;exit\r\n")
                        elif cmd == "all":
                            users = sorted(list(bc._user_list))
                            sys.stdout.write(f"{Fore.CYAN}Online: {', '.join(users)}\r\n")
                        elif cmd == "clear": 
                            sys.stdout.write("\033[H\033[J")
                        elif cmd in ("exit", "quit", "kill"): 
                            raise KeyboardInterrupt
                        elif cmd == "nick" and len(parts) > 1:
                            old = bc.username
                            bc.username = parts[1]
                            save_mem({"username": bc.username})
                            bc.send({"from": "System", "content": f"{old} changed name to {bc.username}"})
                            sys.stdout.write(f"{Fore.YELLOW}System: Your name is now {bc.username}\r\n")
                        
                        input_buffer = ""
                    
                    elif input_buffer.strip():
                        # Local display via broadcaster logic
                        bc.send({"content": input_buffer})
                        bc._print_line({"from": bc.username, "content": input_buffer})
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