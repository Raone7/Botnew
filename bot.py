import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackContext
)


# ========== CONFIG ==========
TOKEN = "7165615313:AAGH8c0eABGxV-NLmv4Cj5K35vJ0Z-KHCFA"

PRIVATE_LINK = "https://t.me/ROGiOSHACKS"

ADMINS = [1456996859]   # Your Telegram ID

UPI_LINK = "raonestore@axl"
CRYPTO_LINK = "contact @RAONEiOSHACKS on telegram"

WEEKLY_PRICE = "$20"
MONTHLY_PRICE = "$50"

DISCOUNT = 30   # % for renewal
# ============================


# Database
conn = sqlite3.connect("subs.db", check_same_thread=False)
cur = conn.cursor()


# Users table
cur.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER,
expiry TEXT,
renewed INTEGER
)
""")

# Payments
cur.execute("""
CREATE TABLE IF NOT EXISTS payments(
user_id INTEGER,
date TEXT,
screenshot TEXT
)
""")

conn.commit()


# Utils
def is_admin(uid):
    return uid in ADMINS


# Start
def start(update, context):

    keyboard = [
        ["📦 Plans", "💳 Subscribe"],
        ["📊 My Status", "📞 Support"]
    ]

    if is_admin(update.message.from_user.id):
        keyboard.append(["🛠 Admin Panel"])

    update.message.reply_text(
        "🔐 Welcome to Premium Channel\n\nChoose option:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# Plans
def plans(update, context):

    update.message.reply_text(
        f"🔥 Plans\n\n"
        f"Weekly: ${WEEKLY_PRICE}\n"
        f"Monthly: ${MONTHLY_PRICE}\n\n"
        f"Renewal Discount: {DISCOUNT}%"
    )


# Subscribe
def subscribe(update, context):

    update.message.reply_text(
        f"💳 Pay First\n\n"
        f"📱 UPI:\n{UPI_LINK}\n\n"
        f"💎 Crypto:\n{CRYPTO_LINK}\n\n"
        f"Then send screenshot here."
    )


# Status
def status(update, context):

    uid = update.message.from_user.id

    cur.execute("SELECT expiry FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()

    if row:
        update.message.reply_text(f"✅ Active till: {row[0]}")
    else:
        update.message.reply_text("❌ Not subscribed")


# Screenshot handler
def screenshot(update, context):

    uid = update.message.from_user.id

    file_id = update.message.photo[-1].file_id

    date = datetime.datetime.now().strftime("%Y-%m-%d")

    cur.execute(
        "INSERT INTO payments VALUES (?,?,?)",
        (uid, date, file_id)
    )
    conn.commit()

    update.message.reply_text("✅ Screenshot received. Waiting approval.")

    for admin in ADMINS:
        context.bot.send_photo(
            admin,
            file_id,
            caption=f"Payment Proof\nUser: {uid}"
        )


# Admin Panel
def admin_panel(update, context):

    if not is_admin(update.message.from_user.id):
        return

    keyboard = [
        ["👥 Users", "📢 Broadcast"],
        ["📈 Stats"]
    ]

    update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# Admin tools
def admin_tools(update, context):

    if not is_admin(update.message.from_user.id):
        return

    text = update.message.text

    if text == "👥 Users":

        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]

        update.message.reply_text(f"Total Users: {count}")

    elif text == "📈 Stats":

        cur.execute("SELECT COUNT(*) FROM payments")
        pay = cur.fetchone()[0]

        update.message.reply_text(f"Payments: {pay}")

    elif text == "📢 Broadcast":

        context.user_data["broadcast"] = True
        update.message.reply_text("Send message to broadcast")


# Broadcast
def broadcast(update, context):

    if not context.user_data.get("broadcast"):
        return

    msg = update.message.text

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    for u in users:
        try:
            context.bot.send_message(u[0], msg)
        except:
            pass

    update.message.reply_text("✅ Broadcast sent")

    context.user_data["broadcast"] = False


# Approve
def approve(update, context):

    if not is_admin(update.message.from_user.id):
        return

    try:
        uid = int(context.args[0])
        plan = context.args[1]

        days = 7 if plan == "weekly" else 30

        cur.execute("SELECT renewed FROM users WHERE user_id=?", (uid,))
        row = cur.fetchone()

        if row:
            days += int(days * DISCOUNT / 100)

        expiry = (datetime.datetime.now() +
                  datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        cur.execute("DELETE FROM users WHERE user_id=?", (uid,))
        cur.execute(
            "INSERT INTO users VALUES (?,?,1)",
            (uid, expiry)
        )
        conn.commit()

        context.bot.send_message(
            uid,
            f"✅ Approved\nValid till: {expiry}\n\nJoin:\n{PRIVATE_LINK}"
        )

        update.message.reply_text("Approved")

    except:
        update.message.reply_text(
            "Usage:\n/approve user_id weekly/monthly"
        )


# Reminders
def reminders(context):

    today = datetime.datetime.now().date()

    cur.execute("SELECT user_id, expiry FROM users")
    rows = cur.fetchall()

    for uid, exp in rows:

        exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()

        if (exp_date - today).days == 2:
            context.bot.send_message(
                uid,
                "⏰ Your subscription expires in 2 days. Renew now!"
            )

        if today > exp_date:
            context.bot.send_message(
                uid,
                "❌ Subscription expired. Please renew."
            )

            cur.execute("DELETE FROM users WHERE user_id=?", (uid,))
            conn.commit()


# Text Handler
def handle(update, context):

    text = update.message.text

    if text == "📦 Plans":
        plans(update, context)

    elif text == "💳 Subscribe":
        subscribe(update, context)

    elif text == "📊 My Status":
        status(update, context)

    elif text == "🛠 Admin Panel":
        admin_panel(update, context)

    elif text in ["👥 Users", "📢 Broadcast", "📈 Stats"]:
        admin_tools(update, context)

    elif text == "📞 Support":
        update.message.reply_text("Contact Admin")

    else:
        broadcast(update, context)


# Main
def main():

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))

    dp.add_handler(MessageHandler(Filters.photo, screenshot))
    dp.add_handler(MessageHandler(Filters.text, handle))

    updater.job_queue.run_daily(
        reminders,
        time=datetime.time(hour=9)
    )

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
