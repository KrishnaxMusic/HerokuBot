import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import time

# -----------------------
# CONFIG
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGO_URL = os.getenv("MONGO_URL")

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------
# MONGO DB SETUP
# -----------------------
client = MongoClient(MONGO_URL)
db = client['usa_bot']
users_col = db['users']

# -----------------------
# TEMP STORAGE
# -----------------------
pending_messages = {}  # {user_id: {'service': ..., 'utr': ..., 'screenshot': ...}}
active_chats = {}      # {user_id: True/False → admin chat mode}
user_stage = {}        # {user_id: 'start'|'service'|'waiting_utr'|'done'}

# -----------------------
# START COMMAND
# -----------------------
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    users_col.update_one({'user_id': user_id}, {'$set': {'user_id': user_id}}, upsert=True)
    user_stage[user_id] = "start"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("˹ʙᴜʏ ʜᴇʀᴏᴋᴜ ᴀᴄᴄᴏᴜɴᴛ˼", callback_data="buy"))
    bot.send_photo(
        msg.chat.id,
        photo="https://files.catbox.moe/if8etf.jpg",
        caption="👋 Wᴇʟᴄᴏᴍᴇ ᴛᴏ Hᴇʀᴏᴋᴜ Bᴏᴛ Sᴇʀᴠɪᴄᴇ!\n🚀 Gᴇᴛ ʏᴏᴜʀ Hᴇʀᴏᴋᴜ sᴇᴛᴜᴘ ʜᴇʀᴇ!\n💼 Cᴏɴᴛᴀᴄᴛ ᴛʜᴇ ᴏᴡɴᴇʀ ғᴏʀ ᴍᴏʀᴇ ᴅᴇᴛᴀɪʟs @BRANDEDKING8",
        reply_markup=kb
    )

# -----------------------
# CALLBACK HANDLER
# -----------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data

    # ---- BUY BUTTON ----
    if data == "buy":
        user_stage[user_id] = "service"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("˹ Hᴇʀᴏᴋᴜ Tᴇᴀᴍ ˼– ₹350", callback_data="buy_Heroku Team"))
        kb.add(InlineKeyboardButton("˹ Hᴇʀᴏᴋᴜ Pᴇʀsᴏɴᴀʟ ˼ – ₹300", callback_data="buy_Heroku Personal"))
        # Safe edit or send
        try:
            if call.message and call.message.message_id:
                bot.edit_message_text("Choose your service:", call.message.chat.id, call.message.message_id, reply_markup=kb)
            else:
                bot.send_message(call.from_user.id, "Choose your service:", reply_markup=kb)
        except:
            bot.send_message(call.from_user.id, "Choose your service:", reply_markup=kb)

    # ---- SERVICE SELECT ----
    elif data.startswith("buy_") and user_stage.get(user_id) == "service":
        service = "Heroku Team" if "Team" in data else "Heroku Personal"
        user_stage[user_id] = "waiting_utr"
        pending_messages[user_id] = {'service': service}
        bot.send_photo(
            call.from_user.id,
            "https://files.catbox.moe/poeeya.jpg",
            caption=f"Sᴄᴀɴ & Pᴀʏ Fᴏʀ {service}\nTʜᴇɴ Sᴇɴᴅ Yᴏᴜʀ *𝟷𝟸 Dɪɢɪᴛ* UTR Nᴜᴍʙᴇʀ Oʀ Sᴄʀᴇᴇɴsʜᴏᴛ Hᴇʀᴇ."
        )

    # ---- ADMIN ACTION ----
    elif data.startswith(("confirm", "cancel", "chat", "endchat")):
        parts = data.split("|")
        action = parts[0]
        target_id = int(parts[1]) if len(parts) > 1 else None

        if not target_id:
            bot.send_message(ADMIN_ID, "⚠️ Invalid callback data.")
            return

        # ---- START CHAT ----
        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 End Chat", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 You are now connected with the admin.")
            bot.send_message(ADMIN_ID, f"💬 Chat started with user {target_id}", reply_markup=kb)
            return

        # ---- END CHAT ----
        if action == "endchat":
            active_chats.pop(target_id, None)
            bot.send_message(target_id, "💬 Chat ended by admin.")
            bot.send_message(ADMIN_ID, f"💬 Chat with user {target_id} ended.")
            return

        # ---- CONFIRM/CANCEL PAYMENT ----
        if target_id not in pending_messages:
            bot.send_message(ADMIN_ID, "⚠️ No pending request from this user.")
            return

        info = pending_messages.pop(target_id)
        service = info.get('service', 'Service')

        if action == "confirm":
            bot.send_message(target_id, f"✅ Payment successful! Generating {service} account…")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💬 Chat with User", callback_data=f"chat|{target_id}"))
            bot.send_message(ADMIN_ID, f"Payment confirmed for user {target_id}.", reply_markup=kb)
        else:
            bot.send_message(target_id, "❌ Payment not received. Your request is cancelled.")
            bot.send_message(ADMIN_ID, f"❌ Payment cancelled for user {target_id}.")

# -----------------------
# FINISH CHAT FUNCTION
# -----------------------
def finish_chat(msg, target_id):
    final_text = msg.text.strip()
    if target_id in active_chats and active_chats[target_id]:
        bot.send_message(target_id, final_text)
        active_chats.pop(target_id, None)
        bot.send_message(ADMIN_ID, f"💬 Chat with user {target_id} ended.")
    else:
        bot.send_message(ADMIN_ID, f"⚠️ No active chat with user {target_id}.")

# -----------------------
# MESSAGE HANDLER
# -----------------------
@bot.message_handler(func=lambda m: True, content_types=['text','photo'])
def chat_handler(msg):
    user_id = msg.from_user.id

    # ---- ADMIN CHAT ----
    if user_id == ADMIN_ID:
        for uid, active in active_chats.items():
            if active:
                bot.send_message(uid, f"🤖Bot: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    # ---- USER CHAT ----
    if user_id in active_chats and active_chats[user_id]:
        bot.send_message(ADMIN_ID, f"💬 User {user_id}: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    stage = user_stage.get(user_id, "none")
    if stage != "waiting_utr":
        bot.send_message(user_id, "⚠️ Please follow the steps or use /start to begin.")
        return

    pending_messages.setdefault(user_id, {})
    user_name = msg.from_user.first_name
    uid = msg.from_user.id
    service = pending_messages[user_id].get('service', 'Service')

    if msg.content_type == 'text':
        text = msg.text.strip()
        if not text.isdigit() or len(text) != 12:
            bot.send_message(user_id, "⚠️ Please enter a valid 12-digit UTR number or send a screenshot.")
            return
        pending_messages[user_id]['utr'] = text
        info_text = f"UTR: {text}"
    elif msg.content_type == 'photo':
        photo_id = msg.photo[-1].file_id
        pending_messages[user_id]['screenshot'] = photo_id
        info_text = "📸 Screenshot sent"

    bot.send_message(user_id, "🔄 Payment request is being verified. Please wait 5–10 seconds…")

    admin_text = (
        f"💰 Payment Request\n"
        f"Name: <a href='tg://user?id={uid}'>{user_name}</a>\n"
        f"User ID: {uid}\n"
        f"Service: {service}\n"
        f"{info_text}"
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{uid}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{uid}")
    )

    if 'screenshot' in pending_messages[user_id]:
        bot.send_photo(ADMIN_ID, pending_messages[user_id]['screenshot'], caption=admin_text, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)

    user_stage[user_id] = "done"


# -----------------------
# BROADCAST COMMAND
# -----------------------
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.chat.id, "⚠️ You are not authorized to use this command.")
        return

    text = msg.text.partition(' ')[2]  # message after /broadcast
    if not text.strip():
        bot.send_message(msg.chat.id, "⚠️ Usage: /broadcast Your message here")
        return

    sent_count, failed_count = 0, 0

    # Get all unique users from MongoDB
    all_users = users_col.find({}, {"user_id": 1})
    for user in all_users:
        user_id = user.get("user_id")
        if not user_id:
            continue
        try:
            bot.send_message(int(user_id), f"📢 Broadcast:\n\n{text}")
            sent_count += 1
            time.sleep(0.05)  # small delay to avoid hitting flood limits
        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to send broadcast to {user_id}: {e}")

    bot.send_message(
        msg.chat.id,
        f"✅ Broadcast finished!\n\n"
        f"📤 Sent: {sent_count}\n"
        f"⚠️ Failed: {failed_count}"
    )


# -----------------------
# RUN BOT
# -----------------------
print("✅ Branded Heroku Bot running…")
bot.infinity_polling()
