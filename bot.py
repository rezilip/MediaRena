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
BOT_TOKEN = "8659065494:AAHdEetxaorQwURQSgLoFOW20NtIEP3LrRo" # توکن خود را بگذارید
ADMIN_ID = 8516792883
CHANNEL_ID = "@MediaRena"
DEV_USERNAME = "irezafattahi"
BOT_USERNAME = "MediaRenaBot"

bot = telebot.TeleBot(BOT_TOKEN)

users = set()
banned_users = set()
pending_downloads = {}

# ================= سرور وب (برای رندر) =================
app = Flask(__name__)
@app.route('/')
def home():
    return "MediaRenaBot is running! 🚀"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ================= کیبوردها =================
def quality_keyboard(dl_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎞 کیفیت 360p", callback_data=f"dl_{dl_id}_360"),
               InlineKeyboardButton("📺 کیفیت 720p (HD)", callback_data=f"dl_{dl_id}_720"))
    markup.row(InlineKeyboardButton("💻 کیفیت 1080p (Full HD)", callback_data=f"dl_{dl_id}_1080"),
               InlineKeyboardButton("⚡ کیفیت بهینه (Auto)", callback_data=f"dl_{dl_id}_best"))
    markup.row(InlineKeyboardButton("🎵 فقط صوت (MP3)", callback_data=f"dl_{dl_id}_mp3"))
    markup.row(InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel"))
    return markup

def back_home_markup(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_home"))
    return markup

def join_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📢 عضویت در کانال رسمی", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"))
    markup.row(InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="verify_join"))
    return markup

def check_join(user_id):
    if not CHANNEL_ID: return True
    if user_id == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['creator', 'administrator', 'member']
    except:
        return True 

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id in banned_users: return
    users.add(chat_id)
    if not check_join(chat_id):
        bot.send_message(chat_id, "⚠️ **لطفاً ابتدا در کانال رسمی ما عضو شوید:**", reply_markup=join_markup(), parse_mode="Markdown")
        return
    text = f"✨ **سلام {message.from_user.first_name} عزیز، خوش آمدید!** 🌹\n\n🤖 به ربات هوشمند **مدیا رنا** خوش آمدید.\n📥 لینک یوتیوب یا شبکه‌های اجتماعی خود را بفرستید:"
    bot.send_message(chat_id, text, reply_markup=back_home_markup(chat_id), parse_mode="Markdown")

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
    bot.reply_to(message, "🎯 **لینک با موفقیت دریافت شد!**\n\n👇 لطفاً کیفیت یا فرمت مورد نظر خود را انتخاب کنید:", reply_markup=quality_keyboard(dl_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in banned_users: return

    if call.data == "verify_join":
        if check_join(chat_id):
            bot.answer_callback_query(call.id, "🎉 عضویت شما تایید شد! حالا لینک خود را بفرستید.", show_alert=True)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید!", show_alert=True)

    elif call.data == "back_home":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        bot.send_message(chat_id, "🏠 **منوی اصلی:** لینک ویدیوی خود را ارسال کنید.", reply_markup=back_home_markup(chat_id), parse_mode="Markdown")

    elif call.data == "cancel":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass

    elif call.data.startswith("dl_"):
        parts = call.data.split("_")
        dl_id = parts[1]
        action = parts[2]
        url = pending_downloads.get(dl_id)
        if not url:
            bot.answer_callback_query(call.id, "❌ این درخواست منقضی شده است.", show_alert=True)
            return
        bot.edit_message_text("⏳ **در حال دانلود و پردازش فایل...** لطفاً صبور باشید.", chat_id, call.message.message_id, parse_mode="Markdown")
        del pending_downloads[dl_id]
        threading.Thread(target=core_downloader, args=(call.message, url, action, dl_id)).start()

def upload_to_cloud(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, data=data, files=files, timeout=60)
            if response.status_code == 200 and response.text.startswith('http'):
                return response.text.strip()
    except Exception as e:
        pass
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
                    self.bot.edit_message_text(f"⏳ **در حال دانلود فایل از سرور...**\n\n`{clean_msg}`", self.chat_id, self.msg_id, parse_mode="Markdown")
                    self.last_update = now
                except:
                    pass
    def warning(self, msg): pass
    def error(self, msg): pass

def core_downloader(message, url, action, dl_id):
    chat_id = message.chat.id
    msg_id = message.message_id
    
    ydl_opts = {
        'outtmpl': f'{dl_id}.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'logger': YTDLLogger(bot, chat_id, msg_id)
    }

    if action == "360": ydl_opts['format'] = 'best[height<=360][filesize<300M]/best[height<=360]'
    elif action == "720": ydl_opts['format'] = 'best[height<=720][filesize<300M]/best[height<=720]'
    elif action == "1080": ydl_opts['format'] = 'best[height<=1080][filesize<300M]/best[height<=1080]'
    elif action == "best": ydl_opts['format'] = 'best[filesize<300M]/best'
    elif action == "mp3":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Media')
            
            files = glob.glob(f"{dl_id}.*")
            if not files: raise Exception("هیچ فایلی دانلود نشد.")
            target_file = files[0]
            file_size = os.path.getsize(target_file)

            if file_size < 50 * 1024 * 1024:
                bot.edit_message_text("✅ **دانلود کامل شد!** در حال ارسال فایل...", chat_id, msg_id, parse_mode="Markdown")
                with open(target_file, 'rb') as f:
                    caption = f"📌 {title}\n\n🤖 دانلود شده توسط ربات مدیا رنا\n@{BOT_USERNAME}"
                    if action == "mp3": 
                        bot.send_audio(chat_id, f, caption=caption, reply_markup=back_home_markup(chat_id))
                    else: 
                        bot.send_video(chat_id, f, caption=caption, reply_markup=back_home_markup(chat_id))
                try:
                    bot.delete_message(chat_id, msg_id)
                except:
                    pass

            else:
                bot.edit_message_text("🚀 **حجم فایل بیش از ۵۰ مگابایت است.** در حال آپلود هوشمند در فضای ابری...", chat_id, msg_id, parse_mode="Markdown")
                cloud_url = upload_to_cloud(target_file)
                
                if cloud_url:
                    msg_text = (f"📌 **{title}**\n\n⚖️ حجم فایل: {round(file_size / (1024*1024), 1)} مگابایت\n🔗 برای دریافت فایل کلیک کنید:\n\n📥 **[لینک دانلود مستقیم]({cloud_url})**")
                    bot.edit_message_text(msg_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_home_markup(chat_id))
                else:
                    bot.edit_message_text("❌ **خطا در آپلود ابری.** لطفاً دوباره تلاش کنید.", chat_id, msg_id, parse_mode="Markdown")

    except Exception as e:
        error_msg = str(e).replace('`', '')[:250]
        bot.edit_message_text(f"❌ **خطا در دانلود یا پردازش ویدیو.**\n\n**دلیل ارور:**\n`{error_msg}...`\n\n*(احتمالاً ویدیو محدودیت دارد یا به پلتفرم متصل نشد)*", chat_id, msg_id, parse_mode="Markdown")
    finally:
        for file in glob.glob(f"{dl_id}.*"):
            try:
                os.remove(file)
            except:
                pass

if __name__ == '__main__':
    print("MediaRenaBot & WebServer started successfully without syntax errors!")
    bot.infinity_polling()
