import sys
import time
import threading
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

SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"

def run_cli():
    room = input("Room id: ")
    username = input("Username: ")
    
    input_buffer = ""
    terminal_lock = threading.Lock()

    def reprint_input():
        sys.stdout.write(f"\r\033[K> {input_buffer}")
        sys.stdout.flush()

    bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username, terminal_lock, reprint_input)

    print(f"{Fore.YELLOW}Connecting...{Style.RESET_ALL}", end="\r")
    while not bc.enabled: time.sleep(0.1)
    sys.stdout.write("\033[K")
    print(f"{Fore.GREEN}Connected to room {room}{Style.RESET_ALL}\n")

    reprint_input()

    try:
        while True:
            char = get_key()
            if char == '\x03': raise KeyboardInterrupt

            with terminal_lock:
                if char in ('\r', '\n'):
                    sys.stdout.write("\r\033[K")
                    
                    if input_buffer.startswith(';'):
                        parts = input_buffer[1:].split()
                        cmd = parts[0].lower() if parts else ""
                        
                        if cmd == "clear":
                            sys.stdout.write("\033[H\033[J")
                        elif cmd in ("exit", "quit", "kill"):
                            raise KeyboardInterrupt
                        elif cmd == "nick" and len(parts) > 1:
                            old_name = bc.username
                            new_name = parts[1]
                            bc.username = new_name
                            print(f"{Fore.YELLOW}System: Your name is now {new_name}{Style.RESET_ALL}")
                            bc.send({"from": "System", "content": f"{old_name} changed their name to {new_name}"})
                        else:
                            print(f"{Fore.RED}Unknown command: {cmd}{Style.RESET_ALL}")
                        
                        input_buffer = ""
                    elif input_buffer.strip():
                        print(f"{Fore.GREEN}[me]{Style.RESET_ALL} {input_buffer}")
                        bc.send({"from": bc.username, "content": input_buffer})
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
        print(f"\r\033[K\n{Fore.RED}Exiting bcli...{Style.RESET_ALL}")
        sys.exit(0)

if __name__ == "__main__":
    run_cli()