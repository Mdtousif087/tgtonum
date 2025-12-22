import os
import asyncio
import re
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

# ============================================================
# CONFIGURATION
# ============================================================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@Itzdhruvusernu_bot")
API_KEY = os.environ.get("API_KEY", "default_key")

# ============================================================
# GLOBALS
# ============================================================
app = Flask(__name__)
client = None
bot_entity = None
loop = None

# ============================================================
# FAST PARSER
# ============================================================
def fast_parse(text: str):
    """Optimized parsing without multiple regex calls"""
    data = {}
    
    if not text:
        return data
    
    # Find all backtick content at once
    backticks = re.findall(r'`([^`]+)`', text)
    
    # Phone usually 2nd backtick (after Country Code)
    if len(backticks) >= 2:
        # Check if it's phone number
        for item in backticks:
            if item.replace('+', '').isdigit() and len(item) >= 10:
                data['phone_number'] = item
                break
    
    # Country (no backticks)
    country_match = re.search(r'Country:\s*([^\n`]+)', text)
    if country_match:
        data['country'] = country_match.group(1).strip()
    
    # Telegram ID (first backtick usually)
    if backticks:
        for item in backticks:
            if item.isdigit() and len(item) >= 8:
                data['telegram_id'] = item
                break
    
    return data

# ============================================================
# TELEGRAM CONNECTION
# ============================================================
def init_telegram():
    """Initialize Telegram connection once"""
    global client, bot_entity, loop
    
    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    # Connect in background
    loop.run_until_complete(client.connect())
    
    if not loop.run_until_complete(client.is_user_authorized()):
        raise Exception("Session not authorized")
    
    bot_entity = loop.run_until_complete(client.get_entity(BOT_USERNAME))
    print(f"✅ Connected to {BOT_USERNAME}")

# ============================================================
# FAST SEARCH FUNCTION
# ============================================================
async def fast_search(user_id: str):
    """Optimized search with minimal delays"""
    try:
        # Send both messages quickly
        await asyncio.gather(
            client.send_message(bot_entity, "Usᴇʀɴᴀᴍᴇ ᴛᴏ ɴᴜᴍ"),
            asyncio.sleep(0.1)
        )
        
        await asyncio.sleep(1)  # Reduced wait
        
        await client.send_message(bot_entity, user_id)
        
        # Wait for response with timeout
        for _ in range(15):  # 15 * 0.5 = 7.5 seconds max
            messages = await client.get_messages(bot_entity, limit=3)
            
            for msg in messages:
                if msg.text and "User Information Lookup" in msg.text:
                    parsed = fast_parse(msg.text)
                    
                    if parsed.get('phone_number'):
                        return {
                            "status": "success",
                            "phone_number": parsed.get('phone_number'),
                            "country": parsed.get('country'),
                            "telegram_id": parsed.get('telegram_id'),
                            "query_id": user_id,
                            "response_time": f"{_ * 0.5:.1f}s",
                            "credit": "MASTEROFOSINTS"
                        }
            
            await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
        return {"status": "error", "message": "Timeout", "credit": "MASTEROFOSINTS"}
        
    except Exception as e:
        return {"status": "error", "message": str(e), "credit": "MASTEROFOSINTS"}

# ============================================================
# API MIDDLEWARE
# ============================================================
def check_key():
    """Fast key verification"""
    key = request.args.get('key')
    return key and key == API_KEY

# ============================================================
# FLASK ROUTES (OPTIMIZED)
# ============================================================
@app.route('/')
def home():
    return jsonify({
        "service": "Fast Telegram Search API",
        "usage": "/search?id=ID&key=KEY",
        "credit": "MASTEROFOSINTS"
    })

@app.route('/search')
def search():
    # Fast validation
    if not check_key():
        return jsonify({"error": "Invalid key"}), 403
    
    user_id = request.args.get('id')
    if not user_id or not user_id.isdigit():
        return jsonify({"error": "Invalid ID"}), 400
    
    # Run search
    try:
        result = loop.run_until_complete(fast_search(user_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status():
    return jsonify({
        "status": "online" if client and client.is_connected() else "offline",
        "bot": BOT_USERNAME,
        "credit": "MASTEROFOSINTS"
    })

# ============================================================
# STARTUP
# ============================================================
# Initialize on import (Vercel serverless)
try:
    init_telegram()
    print("🚀 Fast API Ready!")
except Exception as e:
    print(f"❌ Startup error: {e}")

# Vercel handler
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
