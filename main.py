import sys
import time
import threading
from broadcaster import Broadcaster
from colorama import Fore, Style, init

# Try to import msvcrt for Windows or termios for Linux/Mac
try:
    import msvcrt
    def get_key():
        return msvcrt.getch().decode('utf-8', errors='ignore')
except ImportError:
    import tty, termios
    def get_key():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

init(autoreset=True)

SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"

def run_cli():
    room = input("Room id: ")
    username = input("Username: ")
    
    print(f"{Fore.YELLOW}Connecting...{Style.RESET_ALL}", end="\r")
    
    terminal_lock = threading.Lock()
    bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username, terminal_lock)

    while not bc.enabled:
        time.sleep(0.1)

    sys.stdout.write("\033[K")
    print(f"{Fore.GREEN}Connected to room {room}{Style.RESET_ALL}\n")

    input_buffer = ""
    sys.stdout.write("> ")
    sys.stdout.flush()

    try:
        while True:
            char = get_key()

            with terminal_lock:
                if char in ('\r', '\n'):  # Enter key
                    if input_buffer.strip():
                        # Clear the current typing line
                        sys.stdout.write("\r\033[K")
                        print(f"{Fore.GREEN}[me]{Style.RESET_ALL} {input_buffer}")
                        
                        bc.send({"from": username, "content": input_buffer})
                        input_buffer = ""
                    
                    sys.stdout.write("> ")
                    sys.stdout.flush()

                elif char in ('\x7f', '\x08'):  # Backspace
                    if len(input_buffer) > 0:
                        input_buffer = input_buffer[:-1]
                        sys.stdout.write("\b \b") # Move back, overwrite with space, move back
                        sys.stdout.flush()

                elif ord(char) >= 32:  # Printable characters
                    input_buffer += char
                    sys.stdout.write(char)
                    sys.stdout.flush()

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Exiting...{Style.RESET_ALL}")

if __name__ == "__main__":
    run_cli()