from monitor import extract_budget, matches, parse_feed

SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <item>
    <title><![CDATA[Написать парсер цен конкурентов (Бюджет: 3 000 ₽)]]></title>
    <link>https://www.fl.ru/projects/1/parser.html</link>
    <description><![CDATA[Нужно собрать цены с <b>двух сайтов</b> в Excel]]></description>
    <category>Программирование / Парсинг данных</category>
    <pubDate>Mon, 28 Sep 2026 10:15:00 +0300</pubDate>
  </item>
  <item>
    <title>Нарисовать логотип</title>
    <link>https://www.fl.ru/projects/2/logo.html</link>
    <description>Логотип для кофейни</description>
    <category>Дизайн</category>
  </item>
</channel></rss>"""


def test_parse_feed():
    orders = parse_feed(SAMPLE)
    assert len(orders) == 2
    first = orders[0]
    assert first["title"] == "Написать парсер цен конкурентов (Бюджет: 3 000 ₽)"
    assert first["budget"] == 3000
    assert first["date"] == "28.09.2026 10:15"
    assert "двух сайтов" in first["description"] and "<b>" not in first["description"]
    assert orders[1]["budget"] is None and orders[1]["date"] == ""


def test_filter_by_keywords():
    parser_order, logo_order = parse_feed(SAMPLE)
    assert matches(parser_order, ["парсер"])
    assert not matches(logo_order, ["парсер", "python"])


def test_extract_budget():
    assert extract_budget("Бюджет: 15000 руб") == 15000
    assert extract_budget("Цена договорная") is None
