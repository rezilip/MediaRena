import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import threading
import uuid
import time
import re
import glob
import requests
from flask import Flask

# ================= تنظیمات اختصاصی ربات =================
BOT_TOKEN = "8659065494:AAEyt2G0QBUDi0icUCGhCMdBuNtzz-TsRCE"
ADMIN_ID = 8516792883
CHANNEL_ID = "@MediaRena"
DEV_USERNAME = "irezafattahi"
BOT_USERNAME = "MediaRenaBot"

DONATE_CARD = "۶۰۳۷-۹۹۹۹-۹۹۹۹-۹۹۹۹"
DONATE_NAME = "علیرضا فتاحی"
DONATE_CRYPTO = "TX... (TRC20)"

bot = telebot.TeleBot(BOT_TOKEN)
users = set()
banned_users = set()
pending_downloads = {}

# ================= سرور وب =================
app = Flask(__name__)
@app.route('/')
def home():
    return "MediaRenaBot is completely bulletproof now! 🚀"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ================= کیبوردها =================
def main_menu_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("📥 دانلود مدیا (ارسال لینک)", callback_data="download_section"))
    markup.add(
        InlineKeyboardButton("📖 راهنمای استفاده", callback_data="help"),
        InlineKeyboardButton("📞 پشتیبانی", callback_data="support")
    )
    markup.add(InlineKeyboardButton("☕️ حمایت مالی (Donate)", callback_data="donate"))
    return markup

def back_home_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_home"))
    return markup

def join_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📢 عضویت در کانال رسمی", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"))
    markup.row(InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="verify_join"))
    return markup

def quality_keyboard(dl_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔻 کیفیت پایین (حجم کم)", callback_data=f"dl_{dl_id}_low"))
    markup.row(InlineKeyboardButton("🌟 کیفیت عالی / بهینه", callback_data=f"dl_{dl_id}_high"))
    markup.row(InlineKeyboardButton("🎵 فقط صوت (کیفیت اصلی)", callback_data=f"dl_{dl_id}_mp3"))
    markup.row(InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel"))
    return markup

def check_join(user_id):
    if not CHANNEL_ID: return True
    if user_id == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['creator', 'administrator', 'member']
    except:
        return True 

# ================= دستورات اصلی =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id in banned_users: return
    users.add(chat_id)
    if not check_join(chat_id):
        bot.send_message(chat_id, "⚠️ **دسترسی محدود است!**\n\nجهت استفاده از خدمات، لطفاً ابتدا در کانال رسمی ما عضو شوید:", reply_markup=join_markup(), parse_mode="Markdown")
        return
    text = f"✨ **سلام {message.from_user.first_name} عزیز، خوش آمدید!** 🌹\n\n🤖 به ربات هوشمند و پیشرفته **مدیا رنا** خوش آمدید.\n\n👇 برای شروع، گزینه **«دانلود مدیا»** را انتخاب کنید یا لینک خود را مستقیم بفرستید:"
    bot.send_message(chat_id, text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@bot.message_handler(regexp=r'https?://(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com)/.+')
def handle_links(message):
    chat_id = message.chat.id
    if chat_id in banned_users: return
    if not check_join(chat_id):
        bot.send_message(chat_id, "⚠️ لطفاً ابتدا در کانال عضو شوید:", reply_markup=join_markup())
        return
    users.add(chat_id)
    url = message.text
    dl_id = str(uuid.uuid4())[:8]
    pending_downloads[dl_id] = url
    bot.reply_to(message, "🎯 **لینک با موفقیت شناسایی شد!**\n\n👇 لطفاً کیفیت مورد نظر خود را انتخاب کنید:", reply_markup=quality_keyboard(dl_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in banned_users: return

    if call.data == "verify_join":
        if check_join(chat_id):
            bot.answer_callback_query(call.id, "🎉 عضویت شما تایید شد!", show_alert=True)
            try: bot.delete_message(chat_id, call.message.message_id); except: pass
            bot.send_message(chat_id, "🏠 **منوی اصلی:**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید!", show_alert=True)

    elif call.data == "download_section":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id); except: pass
        bot.send_message(chat_id, "📥 **بخش دانلودر هوشمند:**\n\nلینک ویدیو، پست یا ریلز خود را بفرستید.\n\nپلتفرم‌های پشتیبانی‌شده:\n📺 **یوتیوب** | 📸 **اینستاگرام**\n🎵 **تیک‌تاک** | 🐦 **توییتر (X)**", reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "help":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id); except: pass
        bot.send_message(chat_id, f"📖 **راهنمای جامع:**\n\n**۱.** لینک ویدیو را بفرستید و کیفیت را انتخاب کنید.\n**۲.** حجم زیر ۵۰ مگابایت مستقیم ارسال می‌شود.\n**۳.** حجم بین ۵۰ تا ۲۰۰ مگابایت در فضای ابری آپلود شده و لینک پرسرعت دریافت می‌کنید.\n\n📢 **کانال:** {CHANNEL_ID}\n👨‍💻 **سازنده:** `@{DEV_USERNAME}`", reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "support":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id); except: pass
        msg = bot.send_message(chat_id, "📞 **ارتباط با پشتیبانی:**\n\nپیام خود را کامل بنویسید و ارسال کنید:", reply_markup=back_home_markup(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_support_message)

    elif call.data == "donate":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id); except: pass
        bot.send_message(chat_id, f"☕️ **حمایت مالی:**\n\nاگر این ربات برای شما کاربردی بوده، با حمایت مالی به زنده ماندن این پروژه کمک کنید! ❤️\n\n💳 **کارت:** `{DONATE_CARD}`\n🪙 **تتر/ترون:** `{DONATE_CRYPTO}`", reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "back_home":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id); except: pass
        bot.send_message(chat_id, "🏠 **منوی اصلی:**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

    elif call.data == "cancel":
        try: bot.delete_message(chat_id, call.message.message_id); except: pass

    elif call.data.startswith("dl_"):
        parts = call.data.split("_")
        dl_id = parts[1]
        action = parts[2]
        url = pending_downloads.get(dl_id)
        if not url:
            bot.answer_callback_query(call.id, "❌ درخواست منقضی شده است. لینک را دوباره بفرستید.", show_alert=True)
            return
        bot.edit_message_text("⏳ **در حال دریافت مستقیم فایل...** لطفاً صبور باشید.", chat_id, call.message.message_id, parse_mode="Markdown")
        del pending_downloads[dl_id]
        threading.Thread(target=core_downloader, args=(call.message, url, action, dl_id)).start()

def process_support_message(message):
    if not message.text: return
    try:
        bot.send_message(ADMIN_ID, f"📞 **پیام جدید از پشتیبانی:**\n\n👤 کاربر: {message.from_user.first_name}\n💬 پیام:\n{message.text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ پیام شما ارسال شد.", reply_markup=back_home_markup(message.chat.id))
    except: pass

def upload_to_cloud(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, data=data, files=files, timeout=90)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text.strip()
    except: pass
    return None

class YTDLLogger:
    def __init__(self, bot, chat_id, msg_id):
        self.bot = bot
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.last_update = time.time()
    def debug(self, msg):
        if "[download]" in msg and "%" in msg:
            now = time.time()
            if now - self.last_update > 4: 
                try:
                    clean_msg = re.sub(r'\x1b[^m]*m', '', msg)
                    self.bot.edit_message_text(f"⏳ **در حال دانلود...**\n\n`{clean_msg}`", self.chat_id, self.msg_id, parse_mode="Markdown")
                    self.last_update = now
                except: pass
    def warning(self, msg): pass
    def error(self, msg): pass

def core_downloader(message, url, action, dl_id):
    chat_id = message.chat.id
    msg_id = message.message_id
    
    ydl_opts = {
        'outtmpl': f'{dl_id}.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'logger': YTDLLogger(bot, chat_id, msg_id),
        'cookiefile': 'cookies.txt', # حتما فایل کوکی کنار این کد در گیت هاب باشد
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    }

    # =========================================================
    # فرمت‌های بدون نیاز به مبدل (غیرممکن است ارور فرمت بدهد)
    # =========================================================
    if action == "low":
        ydl_opts['format'] = 'worst' # ضعیف‌ترین فایل آماده
    elif action == "high":
        ydl_opts['format'] = 'best' # بهترین فایل آماده
    elif action == "mp3":
        ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio' # موزیک اصلی بدون نیاز به تبدیل فرمت

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Media')
            
            files = glob.glob(f"{dl_id}.*")
            if not files: raise Exception("فایلی دریافت نشد.")
            target_file = files[0]
            file_size = os.path.getsize(target_file)

            if file_size < 50 * 1024 * 1024:
                bot.edit_message_text("✅ **دانلود کامل شد!** در حال ارسال فایل...", chat_id, msg_id, parse_mode="Markdown")
                with open(target_file, 'rb') as f:
                    caption = f"📌 {title}\n\n🤖 @{BOT_USERNAME}"
                    if action == "mp3": 
                        bot.send_audio(chat_id, f, caption=caption, reply_markup=back_home_markup(chat_id))
                    else: 
                        bot.send_video(chat_id, f, caption=caption, reply_markup=back_home_markup(chat_id))
                try: bot.delete_message(chat_id, msg_id); except: pass

            elif file_size < 200 * 1024 * 1024:
                bot.edit_message_text("🚀 **حجم فایل بیش از ۵۰ مگابایت است.** در حال آپلود ابری (ممکن است ۱ دقیقه زمان ببرد)...", chat_id, msg_id, parse_mode="Markdown")
                cloud_url = upload_to_cloud(target_file)
                if cloud_url:
                    msg_text = f"📌 **{title}**\n\n⚖️ حجم فایل: {round(file_size / (1024*1024), 1)} مگابایت\n🔗 برای دریافت فایل کلیک کنید:\n\n📥 **[لینک دانلود مستقیم]({cloud_url})**"
                    bot.edit_message_text(msg_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_home_markup(chat_id))
                else:
                    bot.edit_message_text("❌ **خطا در اتصال به سرور ابری.**", chat_id, msg_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ **حجم فایل بیشتر از ۲۰۰ مگابایت است.** آپلودسنتر ظرفیت آن را ندارد.", chat_id, msg_id, parse_mode="Markdown")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).replace('`', '')[:250]
        bot.edit_message_text(f"❌ **خطای پردازش:**\n`{error_msg}...`", chat_id, msg_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text("❌ **خطای سیستمی رخ داد.**", chat_id, msg_id, parse_mode="Markdown")
    finally:
        for file in glob.glob(f"{dl_id}.*"):
            try: os.remove(file); except: pass

if __name__ == '__main__':
    bot.infinity_polling()
