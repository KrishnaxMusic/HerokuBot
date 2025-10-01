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
    # Send photo with caption and button
    bot.send_photo(
        msg.chat.id,
        photo="https://files.catbox.moe/if8etf.jpg",   # <-- replace with your own image URL
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
        kb.add(InlineKeyboardButton("Telegram – ₹50", callback_data="buy_telegram"))
        kb.add(InlineKeyboardButton("WhatsApp – ₹45", callback_data="buy_whatsapp"))
        bot.edit_message_text("Choose your service:", call.message.chat.id, call.message.message_id, reply_markup=kb)

        
    # ---- SERVICE SELECT ----
    elif data.startswith("buy_") and user_stage.get(user_id) == "service":
        service = "Heroku" if "Heroku" in data else "Heroku Team"
        user_stage[user_id] = "waiting_utr"
        pending_messages[user_id] = {'service': service}
        bot.send_photo(call.message.chat.id, "https://files.catbox.moe/poeeya.jpg",
                       caption=f"Sᴄᴀɴ & Pᴀʏ Fᴏʀ {service}\nTʜᴇɴ Sᴇɴᴅ Yᴏᴜʀ *𝟷𝟸 Dɪɢɪᴛ* UTR Nᴜᴍʙᴇʀ Oʀ Sᴄʀᴇᴇɴsʜᴏᴛ Hᴇʀᴇ.")

    # ---- ADMIN ACTION ----
    elif data.startswith(("˹ Cᴏɴғɪʀᴍ ˼","˹ Cᴀɴᴄᴇʟ ˼","˹ Cʜᴀᴛ ˼","˹ Eɴᴅᴄʜᴀᴛ ˼")):
        parts = data.split("|")
        action = parts[0]
        target_id = int(parts[1])

        # ---- START CHAT ----
        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 ˹ Eɴᴅ ᴛʜɪs Cʜᴀᴛ ˼", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 ˹ Bᴏᴛ ɪs ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴡɪᴛʜ ʏᴏᴜ ˼")
            bot.send_message(ADMIN_ID, f"💬 ˹ Cʜᴀᴛ sᴛᴀʀᴛᴇᴅ ᴡɪᴛʜ ᴜsᴇʀ ˼ {target_id}", reply_markup=kb)
            return

        # ---- END CHAT ----
        elif action == "˹ Eɴᴅᴄʜᴀᴛ ˼":
            bot.send_message(ADMIN_ID, f"💬 Tʏᴘᴇ ᴛʜᴇ ғɪɴᴀʟ ᴍᴇssᴀɢᴇ ᴛᴏ sᴇɴᴅ ᴛᴏ ᴜsᴇʀ {target_id} ʙᴇғᴏʀᴇ ᴇɴᴅɪɴɢ ᴄʜᴀᴛ:")
            bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda m: finish_chat(m, target_id))
            return

        # ---- CONFIRM/CANCEL PAYMENT ----
        if target_id not in pending_messages:
            bot.send_message(ADMIN_ID, "⚠️ Nᴏ ᴘᴇɴᴅɪɴɢ ʀᴇǫᴜᴇsᴛ ғʀᴏᴍ ᴛʜɪs ᴜsᴇʀ.")
            return

        info = pending_messages.pop(target_id)
        service = info.get('service', 'Service')

        if action == "˹ ᴄᴏɴғɪʀᴍ ˼":
            bot.send_message(target_id, f"✅ Yᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ɪs sᴜᴄᴄᴇssғᴜʟ! Gᴇɴᴇʀᴀᴛɪɴɢ {service} ᴀᴄᴄᴏᴜɴᴛ…")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💬 Cʜᴀᴛ ᴡɪᴛʜ Usᴇʀ", callback_data=f"chat|{target_id}"))
            bot.send_message(ADMIN_ID, f"Pᴀʏᴍᴇɴᴛ ᴄᴏɴғɪʀᴍᴇᴅ ғᴏʀ ᴜsᴇʀ {target_id}.", reply_markup=kb)
        else:
            bot.send_message(target_id, "❌ Yᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ɴᴏᴛ ʀᴇᴄᴇɪᴠᴇᴅ ᴀɴᴅ ʏᴏᴜʀ ǫᴜᴇʀʏ ɪs ᴄᴀɴᴄᴇʟʟᴇᴅ.")
            bot.send_message(ADMIN_ID, f"❌ YPᴀʏᴍᴇɴᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ ғᴏʀ ᴜsᴇʀ. {target_id}.")


# -----------------------
# FINISH CHAT FUNCTION
# -----------------------
def finish_chat(msg, target_id):
    final_text = msg.text.strip()
    if target_id in active_chats and active_chats[target_id]:
        bot.send_message(target_id, final_text)
        active_chats.pop(target_id, None)
        bot.send_message(ADMIN_ID, f"💬 Cʜᴀᴛ ᴡɪᴛʜ Usᴇʀ {target_id} ended.")
    else:
        bot.send_message(ADMIN_ID, f"⚠️ Nᴏ ᴀᴄᴛɪᴠᴇ Cʜᴀᴛ ᴡɪᴛʜ Usᴇʀ {target_id}.")

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
                bot.send_message(uid, f"🤖Bot: {msg.text if msg.content_type=='text' else '📸 Sᴄʀᴇᴇɴsʜᴏᴛ sᴇɴᴛ'}")
        return

    # ---- USER CHAT ----
    if user_id in active_chats and active_chats[user_id]:
        bot.send_message(ADMIN_ID, f"💬 User {user_id}: {msg.text if msg.content_type=='text' else '📸 Sᴄʀᴇᴇɴsʜᴏᴛ sᴇɴᴛ'}")
        return

    stage = user_stage.get(user_id, "none")
    if stage != "waiting_utr":
        bot.send_message(user_id, "⚠️ Pʟᴇᴀsᴇ ғᴏʟʟᴏᴡ ᴛʜᴇ sᴛᴇᴘs ᴏʀ ᴜsᴇ  /start ᴛᴏ ʙᴇɢɪɴ.")
        return

    pending_messages.setdefault(user_id, {})
    user_name = msg.from_user.first_name
    uid = msg.from_user.id
    service = pending_messages[user_id].get('service', 'Service')

    if msg.content_type == 'text':
        text = msg.text.strip()
        if not text.isdigit() or len(text) != 12:
            bot.send_message(user_id, "⚠️ Pʟᴇᴀsᴇ ᴇɴᴛᴇʀ ᴀ ᴠᴀʟɪᴅ *𝟷𝟸 ᴅɪɢɪᴛ* UTR ɴᴜᴍʙᴇʀ ᴏʀ sᴇɴᴅ ᴀ sᴄʀᴇᴇɴsʜᴏ.")
            return
        pending_messages[user_id]['utr'] = text
        info_text = f"UTR: {text}"
    elif msg.content_type == 'photo':
        photo_id = msg.photo[-1].file_id
        pending_messages[user_id]['screenshot'] = photo_id
        info_text = "📸 Sᴄʀᴇᴇɴsʜᴏᴛ sᴇɴᴛ"
    else:
        bot.send_message(user_id, "⚠️ Oɴʟʏ ᴛᴇxᴛ (UTR) ᴏʀ ᴘʜᴏᴛᴏ (sᴄʀᴇᴇɴsʜᴏᴛ) ᴀʟʟᴏᴡᴇᴅ.")
        return

    bot.send_message(user_id, "🔄 Pᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ ɪs ᴠᴇʀɪғʏɪɴɢ ʙʏ ᴏᴜʀ ʀᴇᴄᴏʀᴅs. Pʟᴇᴀsᴇ ᴡᴀɪᴛ 𝟻–𝟷𝟶 sᴇᴄᴏɴᴅs…")

    # ---- SEND ADMIN ----
    admin_text = (
        f"💰 Payment Request\n"
        f"Name: <a href='tg://user?id={uid}'>{user_name}</a>\n"
        f"User ID: {uid}\n"
        f"Service: {service}\n"
        f"{info_text}"
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ ˹ Cᴏɴғɪʀᴍ ˼", callback_data=f"confirm|{uid}"),
        InlineKeyboardButton("❌ ˹ Cᴀɴᴄᴇʟ ˼", callback_data=f"cancel|{uid}")
    )

    if 'screenshot' in pending_messages[user_id]:
        bot.send_photo(ADMIN_ID, pending_messages[user_id]['screenshot'], caption=admin_text, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)

    user_stage[user_id] = "done"

# -----------------------
# COMPLETE COMMAND
# -----------------------
@bot.message_handler(commands=['complete'])
def complete(msg):
    if msg.from_user.id != ADMIN_ID: return
    ended = []
    for uid, active in active_chats.items():
        if active:
            service = pending_messages.get(uid, {}).get('service', 'Service')
            bot.send_message(uid, f"✅ Yᴏᴜʀ {service} ᴘʀᴏᴄᴇss ɪs ᴄᴏᴍᴘʟᴇᴛᴇ. Tʜᴀɴᴋ ʏᴏᴜ ғᴏʀ ᴜsɪɴɢ ᴏᴜʀ ʙᴏᴛ.")
            ended.append(uid)
    for uid in ended:
        active_chats.pop(uid, None)
    bot.send_message(ADMIN_ID, "💬 Aʟʟ ᴀᴄᴛɪᴠᴇ ᴄʜᴀᴛs ᴇɴᴅᴇᴅ.")

# -----------------------
# REFUND COMMAND
# -----------------------
@bot.message_handler(commands=['refund'])
def refund(msg):
    if msg.from_user.id != ADMIN_ID: return
    ended = []
    for uid, active in active_chats.items():
        if active:
            bot.send_message(uid, "❌ Tᴇᴄʜɴɪᴄᴀʟ ɪssᴜᴇ. Yᴏᴜʀ ᴍᴏɴᴇʏ ᴡɪʟʟ ʙᴇ ʀᴇғᴜɴᴅᴇᴅ. Pʟᴇᴀsᴇ ᴡᴀɪᴛ 𝟷𝟶–𝟸𝟶 sᴇᴄᴏɴᴅs…")
            time.sleep(4)
            ended.append(uid)
    for uid in ended:
        active_chats.pop(uid, None)
    bot.send_message(ADMIN_ID, "💬 Rᴇғᴜɴᴅ ᴘʀᴏᴄᴇssᴇᴅ ғᴏʀ ᴀʟʟ ᴀᴄᴛɪᴠᴇ ᴄʜᴀᴛs.")

# -----------------------
# BROADCAST
# -----------------------
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID: return
    text = msg.text.partition(' ')[2]
    if not text:
        bot.reply_to(msg, "⚠️ Usage: /broadcast Yᴏᴜʀ ᴍᴇssᴀɢᴇ ʜᴇʀᴇ")
        return
    sent = 0
    for u in users_col.find():
        try:
            bot.send_message(u['user_id'], f"📢 Bʀᴏᴀᴅᴄᴀsᴛ:\n{text}")
            sent += 1
        except: pass
    bot.reply_to(msg, f"✅ Bʀᴏᴀᴅᴄᴀsᴛ sᴇɴᴛ ᴛᴏ {sent} ᴜsᴇʀs.")

# -----------------------
# RUN BOT
# -----------------------
print("✅ ʙʀᴀɴᴅᴇᴅ ʜᴇʀᴏᴋᴜ ʙᴏᴛ ʀᴜɴɴɪɴɢ…")
bot.infinity_polling()
