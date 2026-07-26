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
BOT_TOKEN = "8659065494:AAHdEetxaorQwURQSgLoFOW20NtIEP3LrRo" # توکن خود را اینجا قرار دهید
ADMIN_ID = 8516792883
CHANNEL_ID = "@MediaRena"
DEV_USERNAME = "irezafattahi"
BOT_USERNAME = "MediaRenaBot"

# اطلاعات حمایت مالی (برای بخش دونیت)
DONATE_CARD = "۶۰۳۷-۹۹۹۹-۹۹۹۹-۹۹۹۹"
DONATE_NAME = "علیرضا فتاحی"
DONATE_CRYPTO = "TX... (TRC20)"

bot = telebot.TeleBot(BOT_TOKEN)
users = set()
banned_users = set()
pending_downloads = {}

# ================= سرور وب (برای روشن ماندن در رندر) =================
app = Flask(__name__)
@app.route('/')
def home():
    return "MediaRenaBot is running and alive! 🚀"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ================= کیبوردهای منظم و قوی =================
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
    markup.row(InlineKeyboardButton("🎞 360p", callback_data=f"dl_{dl_id}_360"),
               InlineKeyboardButton("📺 720p (HD)", callback_data=f"dl_{dl_id}_720"))
    markup.row(InlineKeyboardButton("💻 1080p (FHD)", callback_data=f"dl_{dl_id}_1080"),
               InlineKeyboardButton("⚡ بهینه (Auto)", callback_data=f"dl_{dl_id}_best"))
    markup.row(InlineKeyboardButton("🎵 دانلود صوت (MP3)", callback_data=f"dl_{dl_id}_mp3"))
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
        bot.send_message(chat_id, "⚠️ **دسترسی محدود است!**\n\nجهت استفاده از خدمات رایگان ربات، لطفاً ابتدا در کانال رسمی ما عضو شوید:", reply_markup=join_markup(), parse_mode="Markdown")
        return
        
    text = (
        f"✨ **سلام {message.from_user.first_name} عزیز، خوش آمدید!** 🌹\n\n"
        f"🤖 به ربات هوشمند و پیشرفته **مدیا رنا** خوش آمدید. با این ربات می‌توانید هر ویدیویی را به سادگی دانلود کنید.\n\n"
        f"👇 برای شروع، از منوی زیر گزینه **«دانلود مدیا»** را انتخاب کنید یا لینک خود را مستقیم بفرستید:"
    )
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
    
    bot.reply_to(message, "🎯 **لینک با موفقیت شناسایی شد!**\n\n👇 لطفاً فرمت و کیفیت مورد نظر خود را انتخاب کنید:", reply_markup=quality_keyboard(dl_id), parse_mode="Markdown")

# ================= مدیریت دکمه‌های شیشه‌ای =================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    if chat_id in banned_users: return

    if call.data == "verify_join":
        if check_join(chat_id):
            bot.answer_callback_query(call.id, "🎉 عضویت شما تایید شد!", show_alert=True)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except:
                pass
            bot.send_message(chat_id, "🏠 **منوی اصلی:**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ شما هنوز در کانال عضو نشده‌اید!", show_alert=True)

    elif call.data == "download_section":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        guide_text = (
            "📥 **بخش دانلودر هوشمند:**\n\n"
            "برای دانلود، کافیست لینک ویدیو، پست یا ریلز خود را کپی کرده و در همین صفحه ارسال کنید.\n\n"
            "پلتفرم‌های پشتیبانی‌شده:\n"
            "📺 **یوتیوب** | 📸 **اینستاگرام**\n"
            "🎵 **تیک‌تاک** | 🐦 **توییتر (X)**\n\n"
            "👇 *منتظر دریافت لینک شما هستم...*"
        )
        bot.send_message(chat_id, guide_text, reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "help":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        help_text = (
            "📖 **راهنمای جامع استفاده از ربات:**\n\n"
            "**۱. نحوه دانلود:** لینک ویدیو را کپی کرده و به ربات بفرستید. سپس از منویی که ظاهر می‌شود، کیفیت دلخواه را انتخاب کنید.\n"
            "**۲. محدودیت حجم:** اگر حجم ویدیو کمتر از ۵۰ مگابایت باشد، فایل مستقیم در تلگرام ارسال می‌شود.\n"
            "**۳. فایل‌های سنگین:** اگر حجم ویدیو بین ۵۰ تا ۳۰۰ مگابایت باشد، ربات آن را در فضای ابری آپلود کرده و یک لینک پرسرعت به شما می‌دهد.\n\n"
            f"📢 **کانال رسمی:** {CHANNEL_ID}\n"
            f"👨‍💻 **سازنده:** `@{DEV_USERNAME}`"
        )
        bot.send_message(chat_id, help_text, reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "support":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        support_text = (
            "📞 **ارتباط با پشتیبانی:**\n\n"
            "اگر در دانلود ویدیو مشکلی دارید، ایده جدیدی به ذهنتان رسیده، و یا قصد سفارش ربات دارید، پیام خود را در یک قالب کامل بنویسید و ارسال کنید.\n\n"
            "💬 *لطفاً پیام خود را همین الان تایپ کرده و بفرستید:*"
        )
        msg = bot.send_message(chat_id, support_text, reply_markup=back_home_markup(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_support_message)

    elif call.data == "donate":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        donate_text = (
            "☕️ **حمایت از توسعه‌دهنده (Donate):**\n\n"
            "ربات **مدیا رنا** یک پروژه کاملاً رایگان است. اما نگهداری سرورها، آپدیت کدها و پرداخت هزینه‌های ابری برای ما هزینه‌بر است.\n"
            "اگر این ربات برای شما کاربردی بوده، می‌توانید با حمایت مالی (هرچند کوچک) به زنده ماندن و پیشرفت این پروژه کمک بزرگی کنید! ❤️\n\n"
            f"💳 **شماره کارت:**\n`{DONATE_CARD}`\n👤 به نام: {DONATE_NAME}\n\n"
            f"🪙 **ارز دیجیتال (تتر/ترون):**\n`{DONATE_CRYPTO}`\n\n"
            "🙏 *پیشاپیش از لطف و حمایت شما سپاسگزاریم.*"
        )
        bot.send_message(chat_id, donate_text, reply_markup=back_home_markup(), parse_mode="Markdown")

    elif call.data == "back_home":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        bot.send_message(chat_id, "🏠 **منوی اصلی:**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

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
            bot.answer_callback_query(call.id, "❌ این درخواست منقضی شده است. لطفا لینک را دوباره بفرستید.", show_alert=True)
            return
            
        bot.edit_message_text("⏳ **در حال دور زدن محدودیت‌ها و استخراج فایل...** لطفاً صبور باشید.", chat_id, call.message.message_id, parse_mode="Markdown")
        del pending_downloads[dl_id]
        
        threading.Thread(target=core_downloader, args=(call.message, url, action, dl_id)).start()

# ================= دریافت پیام پشتیبانی =================
def process_support_message(message):
    if not message.text: return
    try:
        bot.send_message(ADMIN_ID, f"📞 **پیام جدید از بخش پشتیبانی:**\n\n👤 فرستنده: {message.from_user.first_name} (`{message.chat.id}`)\n💬 متن پیام:\n{message.text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ پیام شما با موفقیت برای مدیریت ارسال شد. در صورت نیاز با شما تماس خواهیم گرفت.", reply_markup=back_home_markup(message.chat.id))
    except:
        pass

# ================= آپلود ابری =================
def upload_to_cloud(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'reqtype': 'fileupload'}
            response = requests.post(url, data=data, files=files, timeout=90)
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
                    self.bot.edit_message_text(f"⏳ **در حال دریافت اطلاعات و دانلود...**\n\n`{clean_msg}`", self.chat_id, self.msg_id, parse_mode="Markdown")
                    self.last_update = now
                except:
                    pass
    def warning(self, msg): pass
    def error(self, msg): pass

# ================= موتور دانلود =================
def core_downloader(message, url, action, dl_id):
    chat_id = message.chat.id
    msg_id = message.message_id
    
    ydl_opts = {
        'outtmpl': f'{dl_id}.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'logger': YTDLLogger(bot, chat_id, msg_id),
        # ترفند دور زدن ارور تایید هویت یوتیوب (جا زدن به عنوان گوشی اندروید)
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
                bot.edit_message_text("🚀 **حجم فایل بیش از ۵۰ مگابایت است.** در حال آپلود هوشمند در فضای ابری (این مرحله ممکن است ۱ دقیقه زمان ببرد)...", chat_id, msg_id, parse_mode="Markdown")
                cloud_url = upload_to_cloud(target_file)
                
                if cloud_url:
                    msg_text = (f"📌 **{title}**\n\n⚖️ حجم فایل: {round(file_size / (1024*1024), 1)} مگابایت\n🔗 برای دریافت فایل، روی کلمه زیر کلیک کنید:\n\n📥 **[لینک دانلود مستقیم]({cloud_url})**")
                    bot.edit_message_text(msg_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_home_markup(chat_id))
                else:
                    bot.edit_message_text("❌ **خطا در آپلود ابری.** متاسفانه ارتباط با سرور ابری قطع شد.", chat_id, msg_id, parse_mode="Markdown")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).replace('`', '')[:250]
        bot.edit_message_text(f"❌ **خطای امنیتی یوتیوب یا دانلود:**\n\n`{error_msg}...`", chat_id, msg_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text("❌ **خطای پیش‌بینی نشده در پردازش ویدیو رخ داد.**", chat_id, msg_id, parse_mode="Markdown")
    finally:
        for file in glob.glob(f"{dl_id}.*"):
            try:
                os.remove(file)
            except:
                pass

if __name__ == '__main__':
    print("MediaRenaBot is running with Bot Detection Bypass & Advanced Menus!")
    bot.infinity_polling()
