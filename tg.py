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
BOT_USERNAME = os.environ.get("BOT_USERNAME")
API_KEY = os.environ.get("API_KEY")

# ============================================================
# GLOBALS
# ============================================================
app = Flask(__name__)
client = None
bot_entity = None
loop = None

# ============================================================
# CORRECT PARSER
# ============================================================
def parse_bot_response(text: str):
    """Correct parsing for bot format"""
    data = {}
    
    if not text:
        return data
    
    # DEBUG: Show what we're parsing
    print(f"Parsing text: {text[:100]}...")
    
    # 1. Phone Number (EXACT pattern from bot)
    phone_match = re.search(r"Phone Number:\s*`(\+?\d+)`", text)
    if phone_match:
        data['phone_number'] = phone_match.group(1)
        print(f"✅ Found phone: {data['phone_number']}")
    else:
        # Try alternative pattern
        phone_match = re.search(r"📞 Phone Number:\s*`(\+?\d+)`", text)
        if phone_match:
            data['phone_number'] = phone_match.group(1)
            print(f"✅ Found phone (emoji): {data['phone_number']}")
    
    # 2. Country
    country_match = re.search(r"Country:\s*([^\n`]+)", text)
    if country_match:
        country = country_match.group(1).strip()
        # Clean up
        if '└' in country:
            country = country.split('└')[0].strip()
        if '├' in country:
            country = country.split('├')[0].strip()
        data['country'] = country
        print(f"✅ Found country: {data['country']}")
    
    # 3. Country Code
    code_match = re.search(r"Country Code:\s*`(\+\d+)`", text)
    if code_match:
        data['country_code'] = code_match.group(1)
        print(f"✅ Found code: {data['country_code']}")
    
    # 4. Telegram ID (Query ID)
    id_match = re.search(r"Query ID:\s*`(\d+)`", text)
    if id_match:
        data['telegram_id'] = id_match.group(1)
        print(f"✅ Found ID: {data['telegram_id']}")
    
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
    
    # Connect
    loop.run_until_complete(client.connect())
    
    if not loop.run_until_complete(client.is_user_authorized()):
        raise Exception("Session not authorized")
    
    bot_entity = loop.run_until_complete(client.get_entity(BOT_USERNAME))
    print(f"✅ Connected to {BOT_USERNAME}")

# ============================================================
# SEARCH FUNCTION
# ============================================================
async def search_user(user_id: str):
    """Search for user by ID"""
    try:
        # Step 1: Send "Usᴇʀɴᴀᴍᴇ ᴛᴏ ɴᴜᴍ"
        await client.send_message(bot_entity, "Usᴇʀɴᴀᴍᴇ ᴛᴏ ɴᴜᴍ")
        await asyncio.sleep(1)
        
        # Step 2: Send user ID
        await client.send_message(bot_entity, user_id)
        
        # Step 3: Wait for response
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < 3:  # 10 second timeout
            messages = await client.get_messages(bot_entity, limit=3)
            
            for msg in messages:
                if msg.text and "User Information Lookup" in msg.text:
                    parsed = parse_bot_response(msg.text)
                    
                    # Verify we got phone (not user ID)
                    if parsed.get('phone_number') and parsed.get('phone_number') != user_id:
                        return {
                            "status": "success",
                            "phone_number": parsed.get('phone_number'),
                            "country": parsed.get('country'),
                            "country_code": parsed.get('country_code'),
                            "telegram_id": parsed.get('telegram_id'),
                            "query_id": user_id,
                            "credit": "SALAARTHEBOSS"
                        }
                    else:
                        # Phone not found or phone == user_id (wrong)
                        return {
                            "status": "error",
                            "message": f"Parsing issue. Phone: {parsed.get('phone_number')}, Expected different from ID",
                            "parsed_data": parsed,
                            "credit": "SALAARTHEBOSS"
                        }
            
            await asyncio.sleep(0.3)
        
        return {"status": "error", "message": "no data found this number", "credit": "SALAARTHEBOSS"}
        
    except Exception as e:
        return {"status": "error", "message": str(e), "credit": "SALAARTHEBOSS"}

# ============================================================
# API MIDDLEWARE
# ============================================================
def check_key():
    """API key verification"""
    key = request.args.get('key')
    return key and key == API_KEY

# ============================================================
# FLASK ROUTES
# ============================================================
@app.route('/')
def home():
    return jsonify({
        "service": "Telegram User Search API",
        "usage": "GET /search?id=USER_ID&key=API_KEY",
        "credit": "SALAARTHEBOSS"
    })

@app.route('/search')
def search():
    if not check_key():
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    user_id = request.args.get('id')
    if not user_id or not user_id.isdigit():
        return jsonify({"error": "Invalid user ID"}), 400
    
    try:
        result = loop.run_until_complete(search_user(user_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status():
    return jsonify({
        "status": "online" if client and client.is_connected() else "offline",
        "bot": BOT_USERNAME,
        "credit": "SALAARTHEBOSS"
    })

# ============================================================
# STARTUP
# ============================================================
try:
    init_telegram()
    print("🚀 API Ready!")
except Exception as e:
    print(f"❌ Startup error: {e}")

# Vercel handler
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)