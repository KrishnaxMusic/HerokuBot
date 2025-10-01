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

        # Safely edit message, fallback to sending a new message
        try:
            if call.message and call.message.message_id:
                bot.edit_message_text(
                    "Choose your service:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb
                )
            else:
                bot.send_message(call.from_user.id, "Choose your service:", reply_markup=kb)
        except Exception:
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
    elif "|" in data:
        action, target_id = data.split("|")
        target_id = int(target_id)

        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 ˹ Eɴᴅ ᴛʜɪs Cʜᴀᴛ ˼", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 ˹ Bᴏᴛ ɪs ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴡɪᴛʜ ʏᴏᴜ ˼")
            bot.send_message(ADMIN_ID, f"💬 ˹ Cʜᴀᴛ sᴛᴀʀᴛᴇᴅ ᴡɪᴛʜ ᴜsᴇʀ ˼ {target_id}", reply_markup=kb)
            return

        elif action == "endchat":
            bot.send_message(ADMIN_ID, f"💬 Tʏᴘᴇ ᴛʜᴇ ғɪɴᴀʟ ᴍᴇssᴀɢᴇ ᴛᴏ sᴇɴᴅ ᴛᴏ ᴜsᴇʀ {target_id} ʙᴇғᴏʀᴇ ᴇɴᴅɪɴɢ ᴄʜᴀᴛ:")
            bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda m: finish_chat(m, target_id))
            return

        # CONFIRM/CANCEL PAYMENT
        if target_id not in pending_messages:
            bot.send_message(ADMIN_ID, "⚠️ Nᴏ ᴘᴇɴᴅɪɴɢ ʀᴇǫᴜᴇsᴛ ғʀᴏᴍ ᴛʜɪs ᴜsᴇʀ.")
            return

        info = pending_messages.pop(target_id)
        service = info.get('service', 'Service')

        if action == "confirm":
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
# RUN BOT
# -----------------------
print("✅ ʙʀᴀɴᴅᴇᴅ ʜᴇʀᴏᴋᴜ ʙᴏᴛ ʀᴜɴɴɪɴɢ…")
bot.infinity_polling()
