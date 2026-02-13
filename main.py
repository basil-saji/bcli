from broadcaster import Broadcaster
from colorama import Fore, Style, init
import sys
import time

init(autoreset=True)

SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"

def run_cli():
    room = input("Room id: ")
    username = input("Username: ")

    print(f"{Fore.YELLOW}Connecting to {room}...{Style.RESET_ALL}", end="\r")
    
    bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username)

    # Wait for the background thread to enable the connection
    while not bc.enabled:
        time.sleep(0.1)

    # UI FIX: Clear the "Connecting..." line and show clean status
    sys.stdout.write("\033[K") 
    print(f"{Fore.GREEN}Connected to room {room}{Style.RESET_ALL}\n")

    try:
        while True:
            # The prompt is handled here
            text = input("> ")

            if not text.strip():
                # UI FIX: If empty, remove the extra newline/prompt created by pressing Enter
                sys.stdout.write("\033[A\033[K")
                sys.stdout.flush()
                continue

            # UI FIX: Remove the raw user input and replace with [me]
            sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()

            bc.send({
                "from": username,
                "content": text
            })

            print(f"{Fore.GREEN}[me]{Style.RESET_ALL} {text}")
            
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Exiting...{Style.RESET_ALL}")

if __name__ == "__main__":
    run_cli()