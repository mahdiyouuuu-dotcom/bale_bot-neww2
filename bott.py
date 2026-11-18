
# -*- coding: utf-8 -*-
# فروشگاه سکه بله
# Python 3 + requests
# مناسب Pydroid 3

import requests
import sqlite3
import time
import re

# =============== تنظیمات ===============

TOKEN = "942605791:bqcHFoA7kFXNUNW5BUAjbPHJOHfec-cIGWI"
OWNER_ID = 1204403215  # آیدی عددی مدیر

API = f"https://tapi.bale.ai/bot{TOKEN}/"

DB = "coin_shop.db"

# =============== قیمت ها ===============

QUANTITIES = [200, 400, 600, 800, 1000]

PRODUCTS = {
    "bale": {
        "name": "سکه بله",
        "sell": [8500, 17000, 25500, 34000, 41000],
        "buy":  [7600, 15200, 22800, 30400, 38000]
    },
    "cafe": {
        "name": "سکه کافه بله",
        "sell": [3500, 7000, 9500, 13000, 16500],
        "buy":  [2500, 5000, 7500, 10000, 13000]
    },
    "like": {
        "name": "سکه لایک بگیر",
        "sell": [2000, 4000, 6000, 8000, 10000],
        "buy":  [1000, 2000, 4000, 5000, 7000]
    },
    "rubika": {
        "name": "سکه فالوور بگیر روبیکا",
        "sell": [4000, 8000, 12000, 16000, 20000],
        "buy":  [2000, 4000, 8000, 14000, 16000]
    }
}

# =============== دیتابیس ===============

db = sqlite3.connect(DB, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    mode TEXT,
    product TEXT,
    quantity INTEGER,
    price INTEGER,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS states (
    user_id INTEGER PRIMARY KEY,
    state TEXT,
    mode TEXT,
    product TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

db.commit()

# =============== ابزارها ===============

def api(method, data=None):
    try:
        r = requests.post(
            API + method,
            json=data or {},
            timeout=35
        )
        result = r.json()

        if not result.get("ok"):
            print("API ERROR:", result)
        return result

    except Exception as e:
        print("CONNECTION ERROR:", e)
        return {}

def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    result = api("sendMessage", data)
    return bool(result.get("ok"))

def money(number):
    return f"{number:,}"

def set_state(uid, state, mode="", product=""):
    db.execute("""
    INSERT INTO states(user_id,state,mode,product)
    VALUES(?,?,?,?)
    ON CONFLICT(user_id) DO UPDATE SET
    state=excluded.state,
    mode=excluded.mode,
    product=excluded.product
    """, (uid, state, mode, product))
    db.commit()

def get_state(uid):
    return db.execute(
        "SELECT * FROM states WHERE user_id=?",
        (uid,)
    ).fetchone()

def clear_state(uid):
    db.execute("DELETE FROM states WHERE user_id=?", (uid,))
    db.commit()

# =============== منوها ===============

MAIN_MENU = [
    ["🛒 خرید سکه از فروشگاه"],
    ["💰 فروش سکه به فروشگاه"],
    ["📦 پیگیری سفارش"],
    ["🏠 منوی اصلی"]
]

PRODUCT_MENU = [
    ["🟡 سکه بله", "☕ کافه بله"],
    ["❤️ لایک بگیر", "📱 روبیکا"],
    ["🏠 منوی اصلی"]
]

def start(chat_id):
    send(
        chat_id,
        "🪙 به فروشگاه سکه خوش آمدید!\n\n"
        "از منوی زیر عملیات موردنظرتان را انتخاب کنید.",
        MAIN_MENU
    )

def product_key(text):
    mapping = {
        "🟡 سکه بله": "bale",
        "☕ کافه بله": "cafe",
        "❤️ لایک بگیر": "like",
        "📱 روبیکا": "rubika"
    }
    return mapping.get(text)

def show_products(chat_id, mode):
    set_state(
        chat_id,
        "product",
        mode
    )

    send(
        chat_id,
        "یکی از محصولات را انتخاب کنید:",
        PRODUCT_MENU
    )

def show_quantities(chat_id, product):
    set_state(
        chat_id,
        "quantity",
        get_state(chat_id)["mode"],
        product
    )

    p = PRODUCTS[product]

    mode = get_state(chat_id)["mode"]
    prices = p["sell"] if mode == "buy" else p["buy"]

    msg = f"🪙 {p['name']}\n\n"

    for q, price in zip(QUANTITIES, prices):
        label = "۱ کا" if q == 1000 else str(q)
        msg += f"{label} سکه : {money(price)} تومان\n"

    msg += "\nتعداد موردنظر را انتخاب کنید:"

    keyboard = [
        ["۲۰۰ سکه", "۴۰۰ سکه"],
        ["۶۰۰ سکه", "۸۰۰ سکه"],
        ["۱۰۰۰ سکه"],
        ["🏠 منوی اصلی"]
    ]

    send(chat_id, msg, keyboard)

# =============== ثبت سفارش ===============

def create_order(message, product, quantity, mode):

    uid = message["from"]["id"]
    chat_id = message["chat"]["id"]

    user = message.get("from", {})
    first_name = user.get("first_name", "کاربر")
    username = user.get("username", "ندارد")

    index = QUANTITIES.index(quantity)

    prices = (
        PRODUCTS[product]["sell"]
        if mode == "buy"
        else PRODUCTS[product]["buy"]
    )

    price = prices[index]

    db.execute("""
    INSERT INTO orders(
        user_id,username,first_name,
        mode,product,quantity,price,status
    )
    VALUES(?,?,?,?,?,?,?,?)
    """, (
        uid,
        username,
        first_name,
        mode,
        product,
        quantity,
        price,
        "pending"
    ))

    db.commit()

    order_id = db.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    if mode == "buy":
        title = "خرید از فروشگاه"
        action = "درخواست ارسال پاکت"
    else:
        title = "فروش به فروشگاه"
        action = "درخواست فروش سکه به مدیر"

    admin_text = (
        f"🔔 سفارش جدید شماره {order_id}\n\n"
        f"👤 نام: {first_name}\n"
        f"🆔 آیدی: {uid}\n"
        f"🔗 یوزرنیم: @{username}\n"
        f"📦 محصول: {PRODUCTS[product]['name']}\n"
        f"🔢 تعداد: {quantity} سکه\n"
        f"💰 مبلغ: {money(price)} تومان\n"
        f"📋 نوع: {title}\n"
        f"⚙️ عملیات: {action}\n\n"
        f"برای تأیید:\n/done {order_id}\n\n"
        f"برای لغو:\n/cancel {order_id}"
    )

    notified = send(OWNER_ID, admin_text)

    if mode == "buy":
        customer_text = (
            f"✅ سفارش شما ثبت شد.\n\n"
            f"شماره سفارش: {order_id}\n"
            f"محصول: {PRODUCTS[product]['name']}\n"
            f"تعداد: {quantity} سکه\n"
            f"مبلغ: {money(price)} تومان\n\n"
            f"📨 درخواست پاکت برای مدیر ارسال شد.\n"
            f"پس از بررسی و تأیید مدیر، پاکت برایتان ارسال می‌شود.\n\n"
            f"وضعیت: در انتظار بررسی"
        )
    else:
        customer_text = (
            f"✅ درخواست فروش شما ثبت شد.\n\n"
            f"شماره سفارش: {order_id}\n"
            f"محصول: {PRODUCTS[product]['name']}\n"
            f"تعداد: {quantity} سکه\n"
            f"مبلغ پیشنهادی: {money(price)} تومان\n\n"
            f"مدیر درخواست شما را بررسی می‌کند."
        )

    if not notified:
        customer_text += (
            "\n\n⚠️ اطلاع‌رسانی به مدیر ناموفق بود. "
            "لطفاً بعداً پیگیری کنید."
        )

    send(chat_id, customer_text, MAIN_MENU)
    clear_state(uid)

# =============== مدیریت سفارش ===============

def admin_command(uid, chat_id, text):

    if uid != OWNER_ID:
        return False

    match = re.match(r"^/(done|cancel)\s+(\d+)$", text)

    if match:
        action = match.group(1)
        order_id = int(match.group(2))

        order = db.execute(
            "SELECT * FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()

        if not order:
            send(chat_id, "❌ سفارش پیدا نشد.")
            return True

        if order["status"] != "pending":
            send(chat_id, "این سفارش قبلاً تعیین تکلیف شده است.")
            return True

        status = "done" if action == "done" else "cancelled"

        db.execute(
            "UPDATE orders SET status=? WHERE id=?",
            (status, order_id)
        )
        db.commit()

        if status == "done":
            send(
                order["user_id"],
                f"✅ سفارش شماره {order_id} توسط مدیر تأیید شد.\n"
                "اگر خرید پاکت بوده، مدیر باید ارسال آن را انجام داده باشد.",
                MAIN_MENU
            )
            send(chat_id, "سفارش تأیید شد.")
        else:
            send(
                order["user_id"],
                f"❌ سفارش شماره {order_id} لغو شد.",
                MAIN_MENU
            )
            send(chat_id, "سفارش لغو شد.")

        return True

    if text == "/orders":
        orders = db.execute("""
        SELECT * FROM orders
        WHERE status='pending'
        ORDER BY id DESC LIMIT 20
        """).fetchall()

        if not orders:
            send(chat_id, "سفارش در انتظار وجود ندارد.")
            return True

        result = "📋 سفارش‌های در انتظار:\n\n"

        for o in orders:
            result += (
                f"#{o['id']} | {o['first_name']}\n"
                f"{PRODUCTS[o['product']]['name']} - "
                f"{o['quantity']} سکه\n"
                f"{money(o['price'])} تومان\n"
                f"/done {o['id']} | /cancel {o['id']}\n\n"
            )

        send(chat_id, result)
        return True

    return False

# =============== پیگیری ===============

def track_order(uid, chat_id, text):

    try:
        order_id = int(text.strip())
    except ValueError:
        send(chat_id, "شماره سفارش معتبر نیست.")
        return

    order = db.execute("""
    SELECT * FROM orders WHERE id=? AND user_id=?
    """, (order_id, uid)).fetchone()

    if not order:
        send(chat_id, "❌ سفارش پیدا نشد.")
        return

    statuses = {
        "pending": "در انتظار بررسی",
        "done": "تأیید شده",
        "cancelled": "لغو شده"
    }

    send(
        chat_id,
        f"📦 وضعیت سفارش {order_id}\n\n"
        f"محصول: {PRODUCTS[order['product']]['name']}\n"
        f"تعداد: {order['quantity']}\n"
        f"مبلغ: {money(order['price'])} تومان\n"
        f"وضعیت: {statuses.get(order['status'], order['status'])}",
        MAIN_MENU
    )
    clear_state(uid)

# =============== پردازش پیام ===============

def handle_message(message):

    chat_id = message["chat"]["id"]
    uid = message["from"]["id"]
    text = message.get("text", "").strip()

    if message["chat"].get("type") != "private":
        return

    if text in ["/start", "🏠 منوی اصلی"]:
        clear_state(uid)
        start(chat_id)
        return

    if admin_command(uid, chat_id, text):
        return

    if uid == OWNER_ID and text == "/help":
        send(
            chat_id,
            "دستورات مدیر:\n"
            "/orders - سفارش‌های باز\n"
            "/done ID - تأیید سفارش\n"
            "/cancel ID - لغو سفارش"
        )
        return

    state = get_state(uid)

    if text == "🛒 خرید سکه از فروشگاه":
        show_products(chat_id, "buy")
        return

    if text == "💰 فروش سکه به فروشگاه":
        show_products(chat_id, "sell")
        return

    if text == "📦 پیگیری سفارش":
        set_state(uid, "track")
        send(chat_id, "شماره سفارش خود را ارسال کنید.")
        return

    if not state:
        send(chat_id, "برای شروع /start را بزنید.", MAIN_MENU)
        return

    if state["state"] == "track":
        track_order(uid, chat_id, text)
        return

    if state["state"] == "product":
        product = product_key(text)

        if not product:
            send(chat_id, "لطفاً یک محصول از منو انتخاب کنید.", PRODUCT_MENU)
            return

        show_quantities(chat_id, product)
        return

    if state["state"] == "quantity":

        quantity_map = {
            "۲۰۰ سکه": 200,
            "۴۰۰ سکه": 400,
            "۶۰۰ سکه": 600,
            "۸۰۰ سکه": 800,
            "۱۰۰۰ سکه": 1000,
            "1000 سکه": 1000
        }

        quantity = quantity_map.get(text)

        if quantity not in QUANTITIES:
            send(chat_id, "لطفاً تعداد را از دکمه‌ها انتخاب کنید.")
            return

        create_order(
            message,
            state["product"],
            quantity,
            state["mode"]
        )
        return

    send(chat_id, "برای شروع /start را بزنید.", MAIN_MENU)

# =============== دریافت آپدیت ===============

def main():

    if TOKEN == "توکن_ربات_را_اینجا_بگذار":
        print("لطفاً توکن ربات را وارد کنید.")
        return

    if OWNER_ID == 123456789:
        print("لطفاً آیدی عددی مدیر را تنظیم کنید.")
        return

    print("🪙 فروشگاه سکه فعال شد.")

    last_id = 0

    while True:
        try:
            result = api("getUpdates", {
                "offset": last_id + 1,
                "limit": 100,
                "timeout": 25
            })

            if not result.get("ok"):
                time.sleep(3)
                continue

            for update in result.get("result", []):

                last_id = update.get("update_id", last_id)

                message = update.get("message")

                if message:
                    handle_message(message)

        except KeyboardInterrupt:
            print("ربات متوقف شد.")
            break

        except Exception as e:
            print("ERROR:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
