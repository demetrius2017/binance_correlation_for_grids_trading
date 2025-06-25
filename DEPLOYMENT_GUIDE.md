# Развертывание на Vercel

## Проблемы с развертыванием Streamlit на Vercel

Vercel не поддерживает долгоживущие приложения как Streamlit. Вместо этого нужно использовать serverless функции.

## Решения для деплоя:

### 1. Vercel + Flask API (текущее решение)
- ✅ Создан Flask API в `/api/index.py`
- ✅ Веб-интерфейс с HTML/JavaScript
- ✅ Поддержка всех основных функций

**Файлы для Vercel:**
- `vercel.json` - конфигурация
- `api/index.py` - Flask API
- `requirements_vercel.txt` - зависимости

### 2. Рекомендуемые альтернативы:

#### Streamlit Cloud (Лучший вариант для Streamlit)
```bash
# 1. Загрузить код на GitHub
# 2. Зайти на https://share.streamlit.io/
# 3. Подключить репозиторий
# 4. Деплой автоматический
```

#### Heroku
```bash
# Создать Procfile:
echo "web: streamlit run app.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# Деплой:
git init
git add .
git commit -m "Initial commit"
heroku create your-app-name
git push heroku main
```

#### Railway
```bash
# 1. Подключить GitHub репозиторий
# 2. Автоматический деплой Streamlit
# 3. Бесплатный тариф: 500 часов/месяц
```

#### Render
```bash
# 1. Подключить GitHub
# 2. Выбрать Web Service
# 3. Build Command: pip install -r requirements.txt
# 4. Start Command: streamlit run app.py --server.port=\$PORT --server.address=0.0.0.0
```

## Настройка для каждой платформы:

### Для Streamlit Cloud:
1. Переименовать `requirements.txt` (убрать лишние зависимости)
2. Добавить `secrets.toml` для API ключей
3. Загрузить на GitHub

### Для Heroku/Railway/Render:
1. Добавить переменные окружения для API ключей
2. Настроить порт через переменную PORT
3. Использовать существующий `app.py`

## Текущий статус:
- ✅ Flask API готов для Vercel
- ✅ Все основные функции реализованы
- ⚠️ Ограничения Vercel: таймауты, память, CPU

## Рекомендация:
Использовать **Streamlit Cloud** или **Railway** для лучшей совместимости со Streamlit.
