import os
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename
from pymediainfo import MediaInfo

API_ID = 38831490              # Replace with your Telegram API ID
API_HASH = "YOURd8f0dfa3edfa244df7f5623fef10826b"     # Replace with your Telegram API HASH
BOT_TOKEN = "YOUR8953003387:AAEUDPy1HTWbc35-lvgfeYxHzQ8qbEOE4aI"   # Replace with your Bot Token

bot = TelegramClient('bot_session', API_ID, API_HASH)

def generate_response(width: int, height: int, file_ext: str = "Video") -> str:
    # Standard technical definition of 'p': smaller dimension determines the scan-line tier
    p_value = min(width, height)
    orientation = "Portrait (Vertical)" if height > width else "Landscape (Horizontal)"

    # Nearest standard classification
    if p_value >= 2160:
        standard = "4K UHD"
    elif p_value >= 1440:
        standard = "2K QHD"
    elif p_value >= 1080:
        standard = "1080p (Full HD)"
    elif p_value >= 720:
        standard = "720p (HD)"
    elif p_value >= 480:
        standard = "480p (SD)"
    elif p_value >= 360:
        standard = "360p"
    else:
        standard = "Low Resolution"

    ratio = round(max(width, height) / min(width, height), 2)

    # Combined Quick Summary + Detailed Technical Breakdown
    return (
        f"🎯 **Exact Resolution:** `{p_value}p`\n\n"
        f"📋 **Detailed Specifications:**\n"
        f"• **Dimensions:** `{width}x{height}` px\n"
        f"• **Orientation:** `{orientation}`\n"
        f"• **Nearest Standard:** `{standard}`\n"
        f"• **Aspect Ratio:** `~{ratio}:1`\n"
        f"• **Container Format:** `{file_ext.upper()}`"
    )

def extract_metadata_mediainfo(file_path: str):
    """Inspect stream descriptors using MediaInfo without reading full file content."""
    try:
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == "Video":
                w = getattr(track, "width", None)
                h = getattr(track, "height", None)
                if w and h:
                    return int(w), int(h)
    except Exception:
        pass
    return None, None

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(
        "👋 **Video Resolution Inspector Bot**\n\n"
        "Send or forward any video or raw document (MP4, MKV, AVI, FLV, TS, MOV, WMV, etc.) up to 5GB.\n"
        "I will detect the exact **p** resolution and provide an instant summary alongside detailed technical parameters."
    )

@bot.on(events.NewMessage)
async def check_resolution(event):
    if event.text and event.text.startswith('/'):
        return

    msg = event.message
    if not (msg.video or msg.document):
        return

    # Identify file extension
    file_ext = "Video"
    if msg.document:
        for attr in msg.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                _, ext = os.path.splitext(attr.file_name)
                file_ext = ext.lstrip('.').lower() or "Document"
                break

    width, height = None, None

    # Step 1: Read pre-parsed attributes from Telegram if available
    target = msg.video or msg.document
    for attr in target.attributes:
        if isinstance(attr, DocumentAttributeVideo):
            if attr.w and attr.h:
                width, height = attr.w, attr.h
                break

    # Step 2: Stream inspection (reading first 2MB chunk for unindexed documents/MKV/AVI/TS)
    if not (width and height):
        status_msg = await event.reply("🔍 Inspecting video stream header...")
        temp_file = f"sample_{msg.id}.bin"
        try:
            with open(temp_file, 'wb') as f:
                async for chunk in bot.iter_download(msg.media, request_size=2097152):
                    f.write(chunk)
                    break
            
            width, height = extract_metadata_mediainfo(temp_file)
            if os.path.exists(temp_file):
                os.remove(temp_file)
            await status_msg.delete()
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            await status_msg.delete()

    # Step 3: Send formatted response
    if width and height:
        response_text = generate_response(width, height, file_ext)
        await event.reply(response_text, parse_mode='markdown')
    else:
        await event.reply(
            "⚠️ **Could not determine video dimensions.**\n"
            "The file header might be missing or corrupted."
        )

# Web server component to maintain active status on Render Free tier
async def dummy_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await dummy_web_server()
    print("Bot is up and listening for all formats...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
