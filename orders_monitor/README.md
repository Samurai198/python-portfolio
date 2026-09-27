# Монитор заказов с FL.ru

Следит за новыми проектами на FL.ru и присылает только те,
что подходят по словам: python, парсер, бот, excel и т.д.
Пользуюсь сам, чтобы первым откликаться на свежие заказы.

## Как работает

- берёт официальную RSS-ленту `fl.ru/rss/all.xml`, поэтому не ломается от смены вёрстки
- фильтрует по ключевым словам в названии, описании и категории
- вытаскивает бюджет из текста («Бюджет: 3 000 ₽» → `3000`)
- запоминает уже виденные заказы (`seen.json`) и показывает только новые
- сохраняет всё в `orders.xlsx` и, если нужно, шлёт в Telegram

## Запуск

```bash
pip install -r ../requirements.txt
python monitor.py                          # проверить один раз
python monitor.py --watch 10               # проверять каждые 10 минут
python monitor.py --keywords "django,api"  # свои слова
```

Чтобы заказы приходили в Telegram, нужен бот от @BotFather:

```bash
export BOT_TOKEN="токен"
export ADMIN_ID="ваш id от @userinfobot"
python monitor.py --watch 10 --telegram
```

Тесты: `pytest`
