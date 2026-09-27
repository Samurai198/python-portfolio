"""Парсер каталога товаров с выгрузкой в CSV и Excel.

Пример: собирает название, цену, наличие и рейтинг книг
с учебного сайта https://books.toscrape.com (создан специально для парсинга).

Запуск:
    python parser.py --pages 3 --out books
"""

import argparse
import csv
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio parser)"}
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_page(html, page_url):
    """Достаёт товары из HTML одной страницы каталога."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        price_text = card.select_one(".price_color").get_text(strip=True)
        rating_class = card.select_one(".star-rating")["class"][-1]
        items.append({
            "title": link["title"],
            "price": float(price_text.lstrip("£Â")),
            "in_stock": "In stock" in card.select_one(".availability").get_text(),
            "rating": RATINGS.get(rating_class, 0),
            "url": urljoin(page_url, link["href"]),
        })
    return items


def fetch_all(pages, delay=1.0):
    """Скачивает несколько страниц подряд с паузой, чтобы не нагружать сайт."""
    session = requests.Session()
    session.headers.update(HEADERS)
    result = []
    for page in range(1, pages + 1):
        url = BASE_URL.format(page)
        response = session.get(url, timeout=15)
        if response.status_code == 404:
            break
        response.raise_for_status()
        result.extend(parse_page(response.text, url))
        print(f"Страница {page}: всего товаров {len(result)}")
        time.sleep(delay)
    return result


def save_csv(items, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=items[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(items)


def save_xlsx(items, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Товары"
    ws.append(list(items[0].keys()))
    for item in items:
        ws.append(list(item.values()))
    ws.column_dimensions["A"].width = 60
    ws.column_dimensions["E"].width = 70
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description="Парсер каталога товаров")
    ap.add_argument("--pages", type=int, default=1, help="сколько страниц собрать")
    ap.add_argument("--out", default="result", help="имя файла без расширения")
    args = ap.parse_args()

    items = fetch_all(args.pages)
    if not items:
        print("Ничего не найдено")
        return
    save_csv(items, f"{args.out}.csv")
    save_xlsx(items, f"{args.out}.xlsx")
    print(f"Готово: {len(items)} товаров -> {args.out}.csv, {args.out}.xlsx")


if __name__ == "__main__":
    main()
