# 🚀 Быстрый деплой на Railway.com

## Шаг 1: Подготовка

✅ Все файлы готовы
✅ Ошибки кода исправлены  
✅ Конфигурация Railway обновлена

## Шаг 2: Деплой на Railway

1. **Установите Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Логин:**
   ```bash
   railway login
   ```

3. **Инициализация проекта:**
   ```bash
   cd f:\PythonProjects\binance_correlation_script
   railway init
   ```

4. **Деплой:**
   ```bash
   railway up
   ```

## Шаг 3: Настройка переменных окружения (опционально)

```bash
railway variables set FLASK_ENV=production
railway variables set WORKERS=2
```

## Шаг 4: Проверка деплоя

После деплоя Railway предоставит URL вида: `https://your-app.railway.app`

Проверьте:
- ✅ Главная страница: `https://your-app.railway.app/`  
- ✅ Health check: `https://your-app.railway.app/health`

## Ожидаемый результат

🎉 **Полнофункциональное веб-приложение:**
- Grid Trading симуляция
- Автоматическая оптимизация параметров
- Анализ торговых пар Binance
- Красивый веб-интерфейс

## Альтернативные платформы

### Vercel (если у вас Pro план):
```bash
vercel --prod
```

### Render:
1. Подключите GitHub репозиторий
2. Выберите "Web Service"  
3. Команда сборки: `pip install -r requirements.txt`
4. Команда запуска: `gunicorn api.index:app`

## Поддержка

Все файлы проекта готовы к деплою. При возникновении проблем проверьте логи в Railway Dashboard.

**Время деплоя:** ~3-5 минут ⚡
