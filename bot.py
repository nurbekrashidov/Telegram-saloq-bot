import os
import re
import html
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot  # pip install pyTelegramBotAPI

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])

MARKS = [".", ",", "!", "?", ":", ";", "-", "—", "(", ")", '"', "'", "…"]
totals = defaultdict(lambda: defaultdict(int))  # user_id -> belgi -> son
msg_count = defaultdict(int)


def count(text):
    c = defaultdict(int)
    # ko'p nuqta va ellipsis -> bitta "…"
    c["…"] = len(re.findall(r"\.{2,}|…", text))
    text = re.sub(r"\.{2,}|…", " ", text)
    c["—"] = len(re.findall(r"[—–]", text))
    text = re.sub(r"[—–]", " ", text)
    c['"'] = len(re.findall(r'[“”«»"]', text))
    text = re.sub(r'[“”«»"]', " ", text)
    c["'"] = len(re.findall(r"[’‘'ʻʼ`]", text))
    text = re.sub(r"[’‘'ʻʼ`]", " ", text)
    for ch in text:
        if ch in MARKS:
            c[ch] += 1
    return c


def table(c):
    rows = [(m, c[m]) for m in MARKS if c[m]]
    rows.sort(key=lambda r: -r[1])
    total = sum(n for _, n in rows)
    if not total:
        return "Imloviy belgi topilmadi."
    lines = [f"{m}   {n:>4}  {n / total * 100:5.1f}%" for m, n in rows]
    lines.append(f"Jami {total:>4}")
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


@bot.message_handler(commands=["start", "help"])
def start(m):
    bot.reply_to(
        m,
        "Menga matn yuboring yoki xabarlarni forward qiling, belgilarni sanayman.\n"
        "/jami - hozirgacha yuborganlaringiz yig'indisi\n"
        "/reset - yig'indini tozalash",
    )


@bot.message_handler(commands=["jami"])
def jami(m):
    uid = m.from_user.id
    n = msg_count[uid]
    if not n:
        bot.reply_to(m, "Hali xabar yubormadingiz.")
        return
    bot.reply_to(m, f"{n} ta xabar:\n" + table(totals[uid]), parse_mode="HTML")


@bot.message_handler(commands=["reset"])
def reset(m):
    uid = m.from_user.id
    totals[uid].clear()
    msg_count[uid] = 0
    bot.reply_to(m, "Tozalandi.")


@bot.message_handler(content_types=["text"])
def handle(m):
    uid = m.from_user.id
    c = count(m.text)
    for k, v in c.items():
        totals[uid][k] += v
    msg_count[uid] += 1
    bot.reply_to(m, table(c), parse_mode="HTML")


# Render kabi hostinglar port ochilishini kutadi
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def serve():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Ping).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=serve, daemon=True).start()
    bot.infinity_polling()
