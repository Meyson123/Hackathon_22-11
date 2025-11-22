# FastAPI пример для Hackathon Hub

Это упрощённый пример FastAPI приложения для быстрого старта.

## Установка

```bash
pip install -r requirements.txt
```

## Структура

```
fastapi_example/
├── main.py              # Основной файл приложения
├── requirements.txt     # Зависимости
├── templates/           # Jinja2 шаблоны (скопируйте HTML файлы сюда)
├── static/              # Статические файлы
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── script.js
│       └── admin.js
└── users.json          # База данных (создастся автоматически)
```

## Запуск

```bash
# Простой запуск
python main.py

# Или через uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 3000
```

## Миграция HTML файлов

1. Скопируйте все HTML файлы в папку `templates/`
2. Скопируйте CSS в `static/css/`
3. Скопируйте JS в `static/js/`
4. Обновите пути в шаблонах:
   - `href="styles.css"` → `href="{{ url_for('static', path='/css/styles.css') }}"`
   - `src="script.js"` → `src="{{ url_for('static', path='/js/script.js') }}"`

## Пример базового шаблона

Создайте `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Хакатон Хаб{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/css/styles.css') }}">
</head>
<body>
    {% block content %}{% endblock %}
    <script src="{{ url_for('static', path='/js/script.js') }}"></script>
</body>
</html>
```

Затем в других шаблонах:

```html
{% extends "base.html" %}
{% block title %}Главная{% endblock %}
{% block content %}
    <!-- Ваш контент -->
{% endblock %}
```

## Примечания

- Это упрощённый пример для демонстрации
- В продакшене разделите код на модули (см. FASTAPI_MIGRATION.md)
- Используйте переменные окружения для секретных ключей
- Настройте CORS для фронтенда на другом домене

