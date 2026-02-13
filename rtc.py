import asyncio
from supabase import acreate_client
from config import SUPABASE_URL, SUPABASE_KEY, ROOM

supabase = None
channel = None

async def init_rtc(on_message):
    global supabase, channel

    supabase = await acreate_client(SUPABASE_URL, SUPABASE_KEY)

    channel = supabase.channel(ROOM)

    channel.on_broadcast("msg", on_message)

    await channel.subscribe()
