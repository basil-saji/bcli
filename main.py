from broadcaster import Broadcaster
from colorama import Fore, Style, init

init(autoreset=True)

SUPABASE_URL = "https://wqqckkuycvthvizcwfgn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndxcWNra3V5Y3Z0aHZpemN3ZmduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYxNDcxMDYsImV4cCI6MjA4MTcyMzEwNn0.d2mfBuqKG8g4NSLb-EMCnzd-U-_mH35FwOxsbjbuGQ8"


room = input("Room id: ")
username = input("Username: ")

print()  # blank spacing

bc = Broadcaster(SUPABASE_URL, SUPABASE_KEY, room, username)

while True:
    text = input("> ")

    # Remove the raw typed line
    print("\033[A\033[K", end="")

    bc.send({
        "from": username,
        "content": text
    })

    # Print formatted version
    print(f"{Fore.GREEN}[me]{Style.RESET_ALL} {text}")
