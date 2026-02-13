from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, ROOM

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
channel = supabase.channel(ROOM)

def on_message(payload):
    data = payload["payload"]
    sender = data["from"]
    msg = data["content"]

    print(f"\n[{sender}] {msg}")

channel.on_broadcast("msg", on_message)
channel.subscribe()
