"""Монитор новых заказов на фриланс-биржах (FL.ru, Хабр Фриланс).

Читает официальные RSS-ленты проектов, оставляет только заказы
с нужными словами (python, парсер, бот...) и:
  - дописывает их в orders.xlsx,
  - по желанию присылает новые заказы в Telegram.

Уже виденные заказы запоминаются в seen.json, поэтому при повторном
запуске показываются только новые.

Запуск:
    python monitor.py                      # один раз проверить
    python monitor.py --watch 10           # проверять каждые 10 минут
    python monitor.py --telegram           # + слать новые заказы в Telegram

Для Telegram положите рядом файл .env с двумя строками:
    BOT_TOKEN=токен от @BotFather
    ADMIN_ID=ваш числовой id от @userinfobot
"""

import argparse
import html
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from openpyxl import Workbook, load_workbook

FEEDS = {
    "FL.ru": "https://www.fl.ru/rss/all.xml",
    "Хабр Фриланс": "https://freelance.habr.com/tasks.rss",
}
KEYWORDS = ["python", "питон", "парсер", "парсинг", "бот", "telegram",
            "телеграм", "excel", "скрипт", "автоматизац"]
SEEN_FILE = Path("seen.json")
XLSX_FILE = Path("orders.xlsx")
COLUMNS = ["date", "title", "budget", "category", "link", "source"]
ENV_FILE = Path(__file__).with_name(".env")


def parse_feed(xml_text, source=""):
    """Превращает RSS в список заказов."""
    root = ET.fromstring(xml_text)
    orders = []
    for item in root.iter("item"):
        title = html.unescape(item.findtext("title", "").strip())
        description = html.unescape(item.findtext("description", ""))
        description = re.sub(r"<[^>]+>", " ", description).strip()
        pub_date = item.findtext("pubDate")
        orders.append({
            "date": parsedate_to_datetime(pub_date).strftime("%d.%m.%Y %H:%M") if pub_date else "",
            "title": title,
            "budget": extract_budget(title + " " + description),
            "category": item.findtext("category", "").strip(),
            "link": item.findtext("link", "").strip(),
            "description": description,
            "source": source,
        })
    return orders


def extract_budget(text):
    """Ищет в тексте бюджет вида «Бюджет: 3 000 ₽» и возвращает число."""
    match = re.search(r"Бюджет:\s*([\d\s]+)", text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def matches(order, keywords):
    """Ищет слова только с начала слова: «бот» найдёт «боты», но не «работа»."""
    text = f"{order['title']} {order['description']} {order['category']}".lower()
    return any(re.search(r"\b" + re.escape(word), text) for word in keywords)


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False), encoding="utf-8")


def append_xlsx(orders):
    if XLSX_FILE.exists():
        wb = load_workbook(XLSX_FILE)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Заказы"
        ws.append(COLUMNS)
        for column, width in zip("ABCDEF", (17, 70, 10, 35, 50, 15)):
            ws.column_dimensions[column].width = width
    if ws["F1"].value is None:  # файл от старой версии без колонки source
        ws["F1"] = "source"
    for order in orders:
        ws.append([order[c] for c in COLUMNS])
    wb.save(XLSX_FILE)


def send_telegram(orders):
    token, chat_id = os.environ["BOT_TOKEN"], os.environ["ADMIN_ID"]
    for order in orders:
        budget = f"{order['budget']} ₽" if order["budget"] else "не указан"
        text = f"🆕 [{order['source']}] {order['title']}\nБюджет: {budget}\n{order['link']}"
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data={"chat_id": chat_id, "text": text}, timeout=15)
        response.raise_for_status()


def load_env():
    """Читает BOT_TOKEN и ADMIN_ID из файла .env, если он есть."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():  # -sig: Блокнот добавляет BOM
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


def fetch_orders():
    """Собирает заказы со всех лент; если одна биржа недоступна, остальные работают."""
    orders = []
    for source, url in FEEDS.items():
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            response.raise_for_status()
            orders.extend(parse_feed(response.content, source))
        except (requests.RequestException, ET.ParseError) as e:
            print(f"{source}: не удалось получить ленту ({e})")
    return orders


def check(keywords, telegram):
    seen = load_seen()
    new, links = [], set()
    for order in fetch_orders():
        if order["link"] not in seen and order["link"] not in links and matches(order, keywords):
            new.append(order)
            links.add(order["link"])
    if new:
        # Сначала Telegram: если отправка упадёт, заказы не запишутся как «виденные»
        if telegram:
            send_telegram(new)
        append_xlsx(new)
        seen.update(o["link"] for o in new)
        save_seen(seen)
    for order in new:
        print(f"[{order['date']}] [{order['source']}] {order['title']}\n    {order['link']}")
    print(f"Новых подходящих заказов: {len(new)}")


def main():
    ap = argparse.ArgumentParser(description="Монитор заказов FL.ru и Хабр Фриланс")
    ap.add_argument("--watch", type=int, metavar="MIN", help="проверять каждые MIN минут")
    ap.add_argument("--telegram", action="store_true", help="слать новые заказы в Telegram")
    ap.add_argument("--keywords", help="свои слова через запятую, например: django,api")
    args = ap.parse_args()

    keywords = [w.strip().lower() for w in args.keywords.split(",")] if args.keywords else KEYWORDS
    if args.telegram:
        load_env()
        if not os.environ.get("BOT_TOKEN") or not os.environ.get("ADMIN_ID", "").isdigit():
            raise SystemExit("Для --telegram нужен файл .env с BOT_TOKEN и ADMIN_ID, см. README")
    while True:
        try:
            check(keywords, args.telegram)
        except requests.RequestException as e:
            print(f"Не удалось отправить в Telegram: {e}")
        if not args.watch:
            break
        time.sleep(args.watch * 60)


if __name__ == "__main__":
    main()
