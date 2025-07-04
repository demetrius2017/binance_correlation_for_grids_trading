# Анализатор торговых пар Binance с Grid Trading

Комплексная система для автоматического анализа торговых пар на криптовалютной бирже Binance с возможностями симуляции Grid Trading и автоматической оптимизации параметров.

## 🚀 Новые возможности

### 🤖 Автоматическая оптимизация параметров
- Генетический алгоритм и адаптивный поиск
- Разделение данных на бэктест и форвард тест (70%/30%)
- Многопоточная обработка для ускорения
- Поиск стабильных и прибыльных настроек

### ⚡ Grid Trading симуляция
- Реалистичная симуляция с комиссиями Binance
- Dual Grid (Long + Short) стратегии
- Различные типы стоп-лоссов
- Детальная статистика и логи сделок

### 🌐 Развертывание в облаке
- **Streamlit Cloud**: Рекомендуемая платформа (бесплатно)
- **Railway**: Простой деплой из GitHub
- **Render**: Автоматические деплои и SSL
- **Vercel**: Flask API версия (экспериментально)
- **Heroku**: Классический вариант
- Подробная документация в `DEPLOYMENT_COMPLETE_GUIDE.md`

## 🌐 Быстрое развертывание

### Вариант 1: Streamlit Cloud (Рекомендуется)
```bash
# 1. Загрузить проект на GitHub
git clone https://github.com/yourusername/binance-analyzer.git
git add .
git commit -m "Deploy to Streamlit Cloud"
git push

# 2. Перейти на https://share.streamlit.io/
# 3. Подключить GitHub репозиторий
# 4. Добавить секреты в настройках приложения
```

### Вариант 2: Railway
```bash
# 1. Подключить GitHub на https://railway.app/
# 2. Выбрать репозиторий
# 3. Добавить переменные окружения:
#    BINANCE_API_KEY = your_api_key
#    BINANCE_API_SECRET = your_api_secret
```

### Вариант 3: Локальный запуск
```bash
git clone https://github.com/yourusername/binance-analyzer.git
cd binance-analyzer
pip install -r requirements.txt
streamlit run app.py
```

📖 **Полное руководство**: См. `DEPLOYMENT_COMPLETE_GUIDE.md`

## Описание проекта

Проект разработан для решения следующих задач:

1. **Отбор торговых пар** по объему, цене и возрасту
2. **Анализ волатильности** и выявление боковых трендов
3. **Корреляционный анализ** для формирования некоррелированного портфеля
4. **Grid Trading симуляция** с реальными комиссиями
5. **Автоматическая оптимизация** параметров Grid Trading
6. **Веб-интерфейс** для удобного анализа и тестирования

## Структура проекта

```
binance_correlation_script/
├── modules/
│   ├── collector.py         # Модуль сбора данных с Binance API
│   ├── processor.py         # Модуль обработки и ранжирования пар
│   ├── correlation.py       # Модуль анализа корреляций
│   ├── portfolio.py         # Модуль построения оптимального портфеля
│   ├── grid_analyzer.py     # Модуль симуляции Grid Trading
│   └── optimizer.py         # 🆕 Модуль автоматической оптимизации
├── app.py                   # Веб-интерфейс на Streamlit
├── config.json.example      # Пример файла конфигурации с API ключами
├── requirements.txt         # Зависимости проекта
├── test_optimizer.py        # 🆕 Тест модуля оптимизации
├── technical_requirements.md # Техническое задание
├── AUTO_OPTIMIZATION_REPORT.md    # 🆕 Отчет о реализации оптимизации
├── OPTIMIZATION_USER_GUIDE.md     # 🆕 Руководство пользователя
└── README.md                # Описание проекта
```

## Требования

- Python 3.x
- Ключи API Binance

## Установка и настройка

1. Клонируйте репозиторий:
   ```
   git clone https://github.com/username/binance_correlation_for_grids_trading.git
   cd binance_correlation_for_grids_trading
   ```

2. Создайте виртуальное окружение и установите зависимости:
   ```
   python -m venv venv
   venv\Scripts\activate  # Для Windows
   # source venv/bin/activate  # Для Linux/Mac
   pip install -r requirements.txt
   ```

3. Создайте файл конфигурации с вашими API ключами Binance:
   ```
   copy config.json.example config.json
   # Отредактируйте config.json, добавив ваши ключи API
   ```

4. Запустите веб-интерфейс:
   ```
   streamlit run app.py
   ```
   ```

## Использование

1. Откройте веб-интерфейс по адресу http://localhost:8501
2. Введите свои API ключи Binance
3. Настройте параметры анализа
4. Нажмите кнопку "Запустить анализ"
5. Просмотрите результаты на соответствующих вкладках

## Функциональность

### Рейтинг пар
- Отображение списка пар, ранжированных по заданным критериям
- Информация о волатильности и диапазоне цены для каждой пары
- Визуальное выделение лучших пар

### Корреляции
- Визуализация матрицы корреляций в виде тепловой карты
- Выделение наименее коррелированных пар для формирования портфеля

### Оптимальный портфель
- Визуализация распределения активов в оптимальном портфеле
- Статистика портфеля (ожидаемая доходность, волатильность, коэффициент Шарпа)
- Таблица с весами активов

### Графики
- Визуализация динамики цен выбранных пар
- Возможность выбора пар для отображения

## Оригинальные скрипты

В рамках проекта также доступны оригинальные Jupyter ноутбуки:

### auto_coin_list.ipynb
Автоматический генератор списка монет, который ищет на Binance наиболее коррелированные торговые пары для выбранной монеты.

### correlation script.ipynb
Jupyter ноутбук, рассчитывающий матрицы корреляции для криптовалютных монет на бирже Binance.

## Автор

Проект разработан по техническому заданию, описанному в файле technical_requirements.md.

## Лицензия

MIT

