# Heroku конфигурация (для справки, НЕ рекомендуется)

## ⚠️ ВНИМАНИЕ: Heroku больше не рекомендуется для этого проекта

### Проблемы с Heroku:
1. **Стоимость:** Минимум $7/месяц (нет бесплатного плана)
2. **Ограничения:** 30-секундный таймаут для HTTP запросов
3. **Память:** Только 512MB RAM на базовом плане
4. **Производительность:** Не подходит для вычислительно сложных задач

### Как деплоить на Heroku (если очень нужно):

```bash
# 1. Установить Heroku CLI
npm install -g heroku

# 2. Логин
heroku login

# 3. Создать приложение
heroku create your-binance-analyzer

# 4. Настроить переменные окружения
heroku config:set BINANCE_API_KEY=your_api_key
heroku config:set BINANCE_API_SECRET=your_api_secret

# 5. Деплой
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Файлы для Heroku (уже есть):
- ✅ `Procfile` - команда запуска
- ✅ `requirements.txt` - зависимости  
- ✅ `app.py` - основное приложение

### Рекомендуемые альтернативы:
1. **Railway** - лучший выбор (бесплатно + мощно)
2. **Streamlit Cloud** - простейший деплой
3. **Google App Engine** - масштабируемо
4. **Render** - хорошая альтернатива

### Стоимость сравнение:
- Heroku: $7+/месяц
- Railway: Бесплатно (до лимитов)
- Streamlit Cloud: Бесплатно
- Render: Бесплатно

## 💡 Итоговая рекомендация: НЕ используйте Heroku для этого проекта
