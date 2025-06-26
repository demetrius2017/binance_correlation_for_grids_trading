"""
Простой веб-интерфейс для анализа и отбора торговых пар Binance с использованием Streamlit.
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from binance.client import Client

from modules.collector import BinanceDataCollector
from modules.processor import DataProcessor
from modules.correlation import CorrelationAnalyzer
from modules.portfolio import PortfolioBuilder
from modules.grid_analyzer import GridAnalyzer
from modules.optimizer import GridOptimizer

# Константы комиссий Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02%
TAKER_COMMISSION_RATE = 0.0005  # 0.05%


# Функции для сохранения и загрузки API ключей
def save_api_keys(api_key: str, api_secret: str) -> None:
    """Сохраняет API ключи в файл config.json"""
    config = {
        "api_key": api_key,
        "api_secret": api_secret
    }
    with open("config.json", "w") as f:
        json.dump(config, f)
    print("API ключи сохранены в config.json")

def load_api_keys() -> Tuple[str, str]:
    """Загружает API ключи из файла config.json или переменных окружения"""
    try:
        # Сначала пробуем загрузить из Streamlit secrets (для Streamlit Cloud)
        if hasattr(st, 'secrets') and 'binance' in st.secrets:
            return st.secrets["binance"]["api_key"], st.secrets["binance"]["api_secret"]
        
        # Затем из переменных окружения (для Heroku, Railway, Render)
        env_api_key = os.getenv("BINANCE_API_KEY")
        env_api_secret = os.getenv("BINANCE_API_SECRET")
        if env_api_key and env_api_secret:
            return env_api_key, env_api_secret
        
        # Наконец из файла config.json (для локального использования)
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
            return config.get("api_key", ""), config.get("api_secret", "")
        return "", ""
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        return "", ""


# Настройка страницы
st.set_page_config(
    page_title="Анализатор торговых пар Binance",
    page_icon="📊",
    layout="wide"
)

# Инициализация состояния сессии
if 'api_keys_saved' not in st.session_state:
    st.session_state.api_keys_saved = False

if 'saved_pairs' not in st.session_state:
    st.session_state.saved_pairs = []

if 'filtered_pairs' not in st.session_state:
    st.session_state.filtered_pairs = []

# Заголовок приложения
st.title("Анализатор торговых пар Binance")
st.markdown("---")

# Боковая панель для ввода API ключей и параметров
with st.sidebar:
    st.header("Настройки API")
    
    # Загружаем сохраненные ключи
    saved_api_key, saved_api_secret = load_api_keys()
    
    api_key = st.text_input(
        "API Key", 
        value=saved_api_key,
        type="password", 
        help="Введите ваш API ключ от Binance"
    )
    api_secret = st.text_input(
        "API Secret", 
        value=saved_api_secret,
        type="password", 
        help="Введите ваш секретный ключ от Binance"
    )
    
    # Кнопка для сохранения ключей
    if st.button("Сохранить ключи"):
        if api_key and api_secret:
            try:
                save_api_keys(api_key, api_secret)
                st.session_state.api_keys_saved = True
                st.success("API ключи успешно сохранены!")
                # Принудительно обновляем интерфейс
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка при сохранении ключей: {e}")
        else:
            st.error("Введите оба ключа для сохранения")
    
    # Показываем статус сохранения ключей
    if st.session_state.api_keys_saved or (api_key and api_secret):
        st.success("✅ API ключи настроены")
    elif not api_key and not api_secret:
        st.warning("⚠️ Введите API ключи для работы с Binance")
    else:
        st.info("💡 Нажмите 'Сохранить ключи' после ввода")
    
    st.markdown("---")
    
    # Параметры анализа
    st.header("Параметры анализа")
    
    # Основные параметры
    min_volume = st.number_input(
        "Мин. объем торгов (USDT)", 
        min_value=1000000, 
        max_value=1000000000, 
        value=10000000,
        step=1000000,
        help="Минимальный объем торгов за 24 часа"
    )
    
    min_price = st.number_input(
        "Мин. цена (USDT)", 
        min_value=0.0001, 
        max_value=100.0, 
        value=0.01,
        step=0.01,
        help="Минимальная цена актива"
    )
    
    max_price = st.number_input(
        "Макс. цена (USDT)", 
        min_value=1.0, 
        max_value=10000.0, 
        value=100.0,
        step=10.0,
        help="Максимальная цена актива"
    )
    
    max_pairs = st.slider(
        "Количество пар для анализа", 
        min_value=5, 
        max_value=100, 
        value=30,
        help="Максимальное количество пар для детального анализа"
    )

# Кнопка запуска анализа
start_analysis = st.button("🚀 Запустить анализ", type="primary")

# Создаем контейнер для логов
log_container = st.container()

# Загружаем сохраненные ключи для использования в Grid Trading
saved_api_key, saved_api_secret = load_api_keys()

# Создаем вкладки (всегда доступны)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚙️ Настройки", 
    "🔍 Фильтр торговых пар", 
    "ℹ️ Информация",
    "📈 Графики",
    "⚡ Grid Trading",
    "🤖 Авто-оптимизация"
])

# Добавляем стили для улучшения интерфейса вкладок (поддержка светлой и темной темы)
st.markdown("""
<style>
/* Основные стили для вкладок */
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
    font-weight: bold;
    margin: 0;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.stTabs [data-baseweb="tab-list"] button {
    height: 50px;
    white-space: pre-wrap;
    border-radius: 4px 4px 0px 0px;
    gap: 4px;
    padding: 10px 15px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

/* Светлая тема */
@media (prefers-color-scheme: light) {
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f0f2f6;
        color: #262730;
        border-color: #d0d0d0;
    }
    
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #e8eaf0;
        border-color: #bbb;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
    }
}

/* Темная тема */
@media (prefers-color-scheme: dark) {
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #2b2b2b;
        color: #fafafa;
        border-color: #4a4a4a;
    }
    
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #3a3a3a;
        border-color: #666;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
    }
}

/* Принудительные стили для темной темы Streamlit */
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button {
    background-color: #2b2b2b !important;
    color: #fafafa !important;
    border-color: #4a4a4a !important;
}

[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button:hover {
    background-color: #3a3a3a !important;
    border-color: #666 !important;
}

[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background-color: #ff4b4b !important;
    color: white !important;
    border-color: #ff4b4b !important;
}

/* Дополнительные селекторы для темной темы */
.stApp[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button {
    background-color: #2b2b2b !important;
    color: #fafafa !important;
    border-color: #4a4a4a !important;
}

.stApp[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button:hover {
    background-color: #3a3a3a !important;
    border-color: #666 !important;
}

.stApp[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background-color: #ff4b4b !important;
    color: white !important;
    border-color: #ff4b4b !important;
}
</style>
""", unsafe_allow_html=True)

# Предопределенный список популярных пар для всех вкладок
popular_pairs = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "LINKUSDT", "DOTUSDT", "LTCUSDT", "UNIUSDT", "SOLUSDT",
    "MATICUSDT", "ICXUSDT", "VETUSDT", "XLMUSDT", "TRXUSDT",
    "ATOMUSDT", "AVAXUSDT", "NEARUSDT", "AAVEUSDT", "ALGOUSDT",
    "MANAUSDT", "SANDUSDT", "CHZUSDT", "FTMUSDT", "HBARUSDT",
    "THETAUSDT", "IOTAUSDT", "EOSUSDT", "DYDXUSDT", "ZILUSDT"
]

# Функции для работы с сохраненными списками пар
def save_pairs_list(pairs_list: List[str], filename: str = "saved_pairs.json") -> None:
    """Сохраняет список пар в файл"""
    try:
        with open(filename, "w") as f:
            json.dump(pairs_list, f)
        st.success(f"Список из {len(pairs_list)} пар сохранен!")
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")

def load_pairs_list(filename: str = "saved_pairs.json") -> List[str]:
    """Загружает список пар из файла"""
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                pairs = json.load(f)
            return pairs
        else:
            return popular_pairs
    except Exception as e:
        st.error(f"Ошибка при загрузке: {e}")
        return popular_pairs

# Вкладка 1: Настройки и фильтр пар
with tab1:
    st.header("💼 Настройки системы")
    
    # Индикатор состояния
    st.subheader("📊 Статус системы")
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        if api_key and api_secret:
            st.success("🔑 API ключи настроены")
        else:
            st.error("🔑 API ключи не настроены")
    
    with col_status2:
        pairs_count = len(st.session_state.saved_pairs) if st.session_state.saved_pairs else 0
        if pairs_count > 0:
            st.success(f"📋 {pairs_count} пар загружено")
        else:
            st.warning("📋 Список пар пустой")
    
    with col_status3:
        if st.session_state.api_keys_saved:
            st.success("💾 Настройки сохранены")
        else:
            st.info("💾 Настройки не сохранены")
    
    st.markdown("---")
    
    # Секция настроек фильтрации пар
    st.subheader("🔍 Фильтр торговых пар")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write("**Управление списком торговых пар:**")
        
        # Загружаем сохраненный список
        if not st.session_state.saved_pairs:
            st.session_state.saved_pairs = load_pairs_list()
        
        # Показываем текущий список
        pairs_text = "\n".join(st.session_state.saved_pairs)
        
        # Текстовое поле для редактирования списка пар
        edited_pairs_text = st.text_area(
            "Список торговых пар (по одной на строку):",
            value=pairs_text,
            height=200,
            help="Введите символы торговых пар, по одному на строку. Например: BTCUSDT"
        )
        
    with col2:
        st.write("**Действия:**")
        
        if st.button("💾 Сохранить список", use_container_width=True):
            new_pairs = [pair.strip().upper() for pair in edited_pairs_text.split('\n') if pair.strip()]
            if new_pairs:
                st.session_state.saved_pairs = new_pairs
                save_pairs_list(new_pairs)
                time.sleep(1)
                st.rerun()
            else:
                st.error("Список пар не может быть пустым")
        
        if st.button("🔄 Загрузить из файла", use_container_width=True):
            loaded_pairs = load_pairs_list()
            if loaded_pairs:
                st.session_state.saved_pairs = loaded_pairs
                st.success("Список загружен из файла!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Не удалось загрузить список из файла")
        
        if st.button("🔧 Сбросить к умолчанию", use_container_width=True):
            st.session_state.saved_pairs = popular_pairs.copy()
            st.success("Список сброшен к умолчанию!")
            time.sleep(1)
            st.rerun()
        
        st.info(f"Текущий список: {len(st.session_state.saved_pairs)} пар")
    
    st.markdown("---")
    
    # Основные параметры анализа с ползунками
    st.subheader("📊 Параметры анализа")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        min_volume_slider = st.slider(
            "Мин. объем торгов (млн USDT)", 
            min_value=1, 
            max_value=1000, 
            value=10,
            step=1,
            help="Минимальный объем торгов за 24 часа в миллионах USDT"
        )
        min_volume_calc = min_volume_slider * 1000000  # Конвертируем в USDT
        
        min_price_slider = st.slider(
            "Мин. цена (USDT)", 
            min_value=0.0001, 
            max_value=10.0, 
            value=0.01,
            step=0.0001,
            format="%.4f",
            help="Минимальная цена актива"
        )
        
    with col_b:
        max_price_slider = st.slider(
            "Макс. цена (USDT)", 
            min_value=1.0, 
            max_value=10000.0, 
            value=100.0,
            step=1.0,
            help="Максимальная цена актива"
        )
        
        max_pairs_slider = st.slider(
            "Количество пар для анализа", 
            min_value=5, 
            max_value=100, 
            value=30,
            help="Максимальное количество пар для детального анализа"
        )
    
    st.markdown("---")
    
    # Отображение текущих настроек
    st.subheader("📋 Текущие параметры")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.metric("Минимальный объем", f"${min_volume_calc:,}")
        st.metric("Диапазон цен", f"${min_price_slider:.4f} - ${max_price_slider:.2f}")
    
    with col_info2:
        st.metric("Максимум пар", max_pairs_slider)
        st.metric("Пар в списке", len(st.session_state.saved_pairs))

# Вкладка 2: Фильтр торговых пар
with tab2:
    st.header("🔍 Фильтр торговых пар")
    
    if start_analysis:
        st.subheader("🔄 Запуск анализа...")
        st.info("Результаты анализа будут отображены здесь")
        
    else:
        st.subheader("📋 Текущий список пар для анализа")
        
        # Используем сохраненный список пар
        current_pairs = st.session_state.saved_pairs if st.session_state.saved_pairs else popular_pairs
        
        # Ограничиваем количество отображаемых пар
        display_pairs = current_pairs[:max_pairs]
        
        pairs_df = pd.DataFrame({
            'Символ': display_pairs,
            'Описание': [f"Торговая пара {pair}" for pair in display_pairs],
            'Статус': ['✅ Готов к анализу'] * len(display_pairs)
        })
        
        st.dataframe(pairs_df, use_container_width=True)
        st.info(f"Отображено {len(display_pairs)} из {len(current_pairs)} пар в списке")
        
        if len(current_pairs) > max_pairs:
            st.warning(f"В списке {len(current_pairs)} пар, но для анализа выбрано только {max_pairs}. Увеличьте лимит в настройках или уменьшите список пар.")

# Вкладка 3: Информация
with tab3:
    st.header("🔗 Информация о системе")
    
    st.subheader("📈 Реальные комиссии Binance")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Maker комиссия", f"{MAKER_COMMISSION_RATE*100:.3f}%", help="Комиссия за создание ордеров")
    with col2:
        st.metric("Taker комиссия", f"{TAKER_COMMISSION_RATE*100:.3f}%", help="Комиссия за исполнение ордеров")
    
    st.markdown("---")
    
    st.subheader("🚀 Возможности системы")
    
    features = [
        ("✅ Анализ торговых пар", "Фильтрация и ранжирование пар по объему и цене"),
        ("✅ Симуляция Grid Trading", "Тестирование сеточной торговли с реальными комиссиями"),
        ("✅ Множественные таймфреймы", "Поддержка 15m, 1h, 4h, 1d данных"),
        ("✅ Стратегии стоп-лосса", "Различные варианты управления рисками"),
        ("✅ Авто-оптимизация", "Генетические алгоритмы для поиска лучших параметров"),
        ("✅ Персистентные настройки", "Сохранение и загрузка списков пар и настроек")
    ]
    
    for emoji_title, description in features:
        with st.container():
            st.write(f"**{emoji_title}**")
            st.write(f"   {description}")
    
    st.markdown("---")
    
    st.subheader("📚 Инструкция по использованию")
    with st.expander("Как начать работу"):
        st.write("""
        1. **Настройте API ключи** в боковой панели (получите их на Binance)
        2. **Настройте параметры** в первой вкладке "Настройки"
        3. **Отредактируйте список пар** для анализа в той же вкладке
        4. **Запустите анализ** кнопкой в боковой панели
        5. **Просмотрите результаты** во вкладке "Фильтр торговых пар"
        6. **Протестируйте Grid Trading** во вкладке "Grid Trading"
        7. **Оптимизируйте параметры** во вкладке "Авто-оптимизация"
        """)
    
    with st.expander("О Grid Trading"):
        st.write("""
        Grid Trading (сеточная торговля) - это стратегия, которая размещает ордера на покупку и продажу 
        через равные интервалы цены вокруг установленной базовой цены, создавая "сетку" ордеров.
        
        **Преимущества:**
        - Может быть прибыльной в боковых рынках
        - Автоматизирует торговлю
        - Позволяет получать прибыль от волатильности
        
        **Риски:**
        - Может привести к убыткам в трендовых рынках
        - Требует достаточного капитала
        - Комиссии могут съедать прибыль
        """)

# Вкладка 4: Графики цен
with tab4:
    st.header("📈 Графики цен")
    
    current_pairs_for_chart = st.session_state.saved_pairs if st.session_state.saved_pairs else popular_pairs
    selected_symbol = st.selectbox(
        "Выберите актив для просмотра", 
        current_pairs_for_chart, 
        key="chart_symbol",
        help=f"Доступно {len(current_pairs_for_chart)} пар из сохраненного списка"
    )
    
    if selected_symbol and api_key and api_secret:
        try:
            with st.spinner(f"Загрузка данных для {selected_symbol}..."):
                collector = BinanceDataCollector(api_key, api_secret)
                df = collector.get_historical_data(selected_symbol, "1d", 90)
            
            if not df.empty:
                # График цены
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(df.index, df['close'], linewidth=2, color='#ff4b4b')
                ax.set_title(f"График цены {selected_symbol} за последние 90 дней", fontsize=16, fontweight='bold')
                ax.set_xlabel("Дата")
                ax.set_ylabel("Цена (USDT)")
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                
                # Базовая статистика
                st.subheader(f"📊 Статистика {selected_symbol}")
                
                col_chart1, col_chart2, col_chart3, col_chart4 = st.columns(4)
                
                with col_chart1:
                    st.metric("Текущая цена", f"${df['close'].iloc[-1]:.6f}")
                with col_chart2:
                    st.metric("Максимум", f"${df['high'].max():.6f}")
                with col_chart3:
                    st.metric("Минимум", f"${df['low'].min():.6f}")
                with col_chart4:
                    price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
                    st.metric("Изменение", f"{price_change:.2f}%")
                    
            else:
                st.warning("Данные для выбранной пары недоступны.")
        except Exception as e:
            st.error(f"Ошибка при получении данных: {str(e)}")
    elif not api_key or not api_secret:
        st.warning("Введите API ключи в боковой панели для просмотра графиков")
    else:
        st.info("Выберите торговую пару для отображения графика")

# Вкладка 5: Grid Trading (всегда доступна)
with tab5:
    st.header("⚡ Симуляция сеточной торговли")

    # Параметры для сеточной торговли
    st.subheader("🎛️ Параметры сетки")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        grid_range_pct = st.slider(
            "Диапазон сетки (%)", 
            min_value=5.0, 
            max_value=50.0, 
            value=20.0,
            step=1.0,
            help="Процентный диапазон для размещения сетки"
        )
    
    with col2:
        grid_step_pct = st.slider(
            "Шаг сетки (%)", 
            min_value=0.1, 
            max_value=5.0, 
            value=1.0,
            step=0.1,
            help="Процентный шаг между уровнями сетки"
        )
        
    with col3:
        initial_balance = st.slider(
            "Начальный баланс (USDT)",
            min_value=100,
            max_value=50000,
            value=1000,
            step=100,
            help="Начальный капитал для симуляции"
        )

    st.markdown("---")
    
    # Дополнительные параметры симуляции
    st.subheader("⚙️ Дополнительные параметры")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        simulation_days = st.slider(
            "Срок симуляции (дни)",
            min_value=7,
            max_value=365,
            value=90,
            step=1,
            help="Количество дней исторических данных для симуляции"
        )
    with col_b:
        stop_loss_pct = st.slider(
            "Стоп-лосс (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.5,
            help="Процент убытка от начального капитала для закрытия всех позиций. 0 - отключить."
        )
    with col_c:
        timeframe = st.selectbox(
            "Таймфрейм",
            options=["15m", "1h", "4h", "1d"],
            index=1,
            help="Таймфрейм для загрузки исторических данных"
        )

    # Выбор пары для симуляции
    current_pairs_for_grid = st.session_state.saved_pairs if st.session_state.saved_pairs else popular_pairs
    selected_pair_for_grid = st.selectbox(
        "Выберите пару для симуляции",
        current_pairs_for_grid,
        key="selected_pair_for_grid",
        help=f"Доступно {len(current_pairs_for_grid)} пар из сохраненного списка"
    )

    if st.button("🚀 Запустить симуляцию для выбранной пары", type="primary"):
        if not saved_api_key or not saved_api_secret:
            st.error("Пожалуйста, введите и сохраните API ключи в боковой панели.")
        elif not selected_pair_for_grid:
            st.warning("Пожалуйста, выберите пару для симуляции.")
        else:
            try:
                # Инициализация инструментов
                with st.spinner("Подключение к Binance..."):
                    collector = BinanceDataCollector(saved_api_key, saved_api_secret)
                    grid_analyzer = GridAnalyzer(collector)
                st.success("Подключение успешно!")
                
                # Получение исторических данных
                with st.spinner(f"Загрузка исторических данных для {selected_pair_for_grid}..."):
                    timeframe_in_minutes = {'15m': 15, '1h': 60, '4h': 240, '1d': 1440}
                    total_minutes = simulation_days * 24 * 60
                    limit = int(total_minutes / timeframe_in_minutes[timeframe])
                    
                    df_for_simulation = collector.get_historical_data(selected_pair_for_grid, timeframe, limit)
                
                if df_for_simulation.empty:
                    st.error("Не удалось загрузить данные для симуляции.")
                else:
                    # Запуск симуляции
                    with st.spinner(f"Запуск симуляции для {selected_pair_for_grid}..."):
                        stats_long, stats_short, log_long_df, log_short_df = grid_analyzer.estimate_dual_grid_by_candles_realistic(
                            df=df_for_simulation,
                            initial_balance_long=initial_balance,
                            initial_balance_short=initial_balance,
                            grid_range_pct=grid_range_pct,
                            grid_step_pct=grid_step_pct,
                            order_size_usd_long=0,  # Автоматический расчет
                            order_size_usd_short=0, # Автоматический расчет
                            commission_pct=TAKER_COMMISSION_RATE * 100,
                            stop_loss_pct=stop_loss_pct if stop_loss_pct > 0 else None,
                            debug=False
                        )

                    st.success(f"✅ Симуляция для {selected_pair_for_grid} за {simulation_days} дней завершена!")
                    
                    # Отображение результатов
                    st.subheader("📊 Результаты симуляции")
                    
                    # Расчет комбинированных результатов
                    total_pnl = stats_long['total_pnl'] + stats_short['total_pnl']
                    total_initial_balance = initial_balance * 2
                    total_pnl_pct = (total_pnl / total_initial_balance) * 100 if total_initial_balance > 0 else 0
                    total_trades = stats_long['trades_count'] + stats_short['trades_count']
                    total_commission = stats_long['total_commission'] + stats_short['total_commission']
                    
                    col_result1, col_result2, col_result3 = st.columns(3)
                    
                    with col_result1:
                        st.metric("Общий PnL", f"${total_pnl:.2f}", f"{total_pnl_pct:.2f}%")
                    with col_result2:
                        st.metric("Всего сделок", total_trades)
                    with col_result3:
                        st.metric("Всего комиссий", f"${total_commission:.2f}")

                    st.subheader("📋 Детальная статистика")
                    
                    results_data = {
                        "Метрика": ["Баланс Long", "PnL Long ($)", "PnL Long (%)", "Сделок Long", "Комиссии Long ($)",
                                    "Баланс Short", "PnL Short ($)", "PnL Short (%)", "Сделок Short", "Комиссии Short ($)"],
                        "Значение": [
                            f"${stats_long['final_balance']:.2f}", f"${stats_long['total_pnl']:.2f}", f"{stats_long['total_pnl_pct']:.2f}%", str(stats_long['trades_count']), f"${stats_long['total_commission']:.2f}",
                            f"${stats_short['final_balance']:.2f}", f"${stats_short['total_pnl']:.2f}", f"{stats_short['total_pnl_pct']:.2f}%", str(stats_short['trades_count']), f"${stats_short['total_commission']:.2f}"
                        ]
                    }
                    # Приводим все значения к строкам для избежания ошибки Arrow
                    results_df = pd.DataFrame(results_data)
                    results_df['Значение'] = results_df['Значение'].astype(str)
                    st.dataframe(results_df, use_container_width=True)

                    # Отображение логов сделок
                    with st.expander("📋 Показать логи сделок"):
                        st.subheader("Лог сделок Long")
                        if log_long_df: # Проверяем, что список не пустой
                            df_long = pd.DataFrame(log_long_df)
                            st.dataframe(df_long, use_container_width=True)
                        else:
                            st.info("Сделок по Long не было.")
                            
                        st.subheader("Лог сделок Short")
                        if log_short_df: # Проверяем, что список не пустой
                            df_short = pd.DataFrame(log_short_df)
                            st.dataframe(df_short, use_container_width=True)
                        else:
                            st.info("Сделок по Short не было.")

            except Exception as e:
                st.error(f"Произошла ошибка во время симуляции: {e}")
                st.exception(e)

# Вкладка 6: Авто-оптимизация
with tab6:
    st.header("🤖 Автоматическая оптимизация параметров")
    
    st.markdown("""
    **Как это работает:**
    - Данные разделяются на бэктест (70%) и форвард тест (30%)
    - Алгоритм ищет параметры, показывающие стабильные результаты на обеих частях
    - Используется генетический алгоритм или адаптивный поиск по сетке
    - Многопоточная обработка для ускорения
    """)
    
    # Параметры оптимизации
    st.subheader("⚙️ Параметры оптимизации")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        current_pairs_for_opt = st.session_state.saved_pairs if st.session_state.saved_pairs else popular_pairs
        opt_pair = st.selectbox(
            "Пара для оптимизации",
            current_pairs_for_opt,
            key="opt_pair",
            help=f"Доступно {len(current_pairs_for_opt)} пар из сохраненного списка"
        )
        
        opt_balance = st.slider(
            "Баланс для тестов (USDT)",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="Начальный капитал для тестирования стратегий"
        )
    
    with col2:
        opt_timeframe = st.selectbox(
            "Таймфрейм",
            options=["15m", "1h", "4h", "1d"],
            index=1,
            key="opt_timeframe"
        )
        
        opt_days = st.slider(
            "Дней истории",
            min_value=30,
            max_value=365,
            value=180,
            help="Общее количество дней данных"
        )
    
    with col3:
        opt_method = st.selectbox(
            "Метод оптимизации",
            options=["Генетический алгоритм", "Адаптивный поиск"],
            help="Генетический - лучше для глобального поиска, Адаптивный - быстрее"
        )
        
        max_workers = st.slider(
            "Потоков",
            min_value=1,
            max_value=8,
            value=4,
            help="Количество параллельных потоков"
        )
    
    # Дополнительные параметры в зависимости от метода
    st.subheader("🎛️ Настройки алгоритма")
    
    # Инициализируем переменные значениями по умолчанию
    population_size = 50
    generations = 20
    iterations = 3
    points_per_iteration = 50
    
    if opt_method == "Генетический алгоритм":
        col_a, col_b = st.columns(2)
        with col_a:
            population_size = st.slider("Размер популяции", 20, 100, 50)
        with col_b:
            generations = st.slider("Поколений", 10, 50, 20)
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            iterations = st.slider("Итераций", 2, 5, 3)
        with col_b:
            points_per_iteration = st.slider("Точек за итерацию", 20, 100, 50)
    
    st.markdown("---")
    
    # Кнопка запуска оптимизации
    if st.button("🚀 Запустить оптимизацию", type="primary", key="start_optimization"):
        if not saved_api_key or not saved_api_secret:
            st.error("Пожалуйста, введите и сохраните API ключи в боковой панели.")
        else:
            try:
                # Прогресс бар и контейнеры для вывода
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Инициализация
                status_text.text("Инициализация...")
                collector = BinanceDataCollector(saved_api_key, saved_api_secret)
                grid_analyzer = GridAnalyzer(collector)
                optimizer = GridOptimizer(grid_analyzer, TAKER_COMMISSION_RATE)
                
                # Загрузка данных
                status_text.text(f"Загрузка данных для {opt_pair}...")
                progress_bar.progress(10)
                
                timeframe_in_minutes = {'15m': 15, '1h': 60, '4h': 240, '1d': 1440}
                total_minutes = opt_days * 24 * 60
                limit = int(total_minutes / timeframe_in_minutes[opt_timeframe])
                
                df_opt = collector.get_historical_data(opt_pair, opt_timeframe, limit)
                
                if df_opt.empty:
                    st.error("Не удалось загрузить данные для оптимизации.")
                else:
                    progress_bar.progress(20)
                    
                    # Функция для обновления прогресса
                    def progress_callback(message):
                        status_text.text(message)
                    
                    start_time = time.time()
                    
                    # Запуск оптимизации в зависимости от выбранного метода
                    if opt_method == "Генетический алгоритм":
                        status_text.text("Запуск генетического алгоритма...")
                        progress_bar.progress(30)
                        
                        results = optimizer.optimize_genetic(
                            df=df_opt,
                            initial_balance=opt_balance,
                            population_size=population_size,
                            generations=generations,
                            forward_test_pct=0.3,
                            max_workers=max_workers,
                            progress_callback=progress_callback
                        )
                    else:
                        status_text.text("Запуск адаптивного поиска...")
                        progress_bar.progress(30)
                        
                        results = optimizer.grid_search_adaptive(
                            df=df_opt,
                            initial_balance=opt_balance,
                            forward_test_pct=0.3,
                            iterations=iterations,
                            points_per_iteration=points_per_iteration,
                            progress_callback=progress_callback
                        )
                    
                    end_time = time.time()
                    progress_bar.progress(100)
                    status_text.text(f"✅ Оптимизация завершена за {end_time - start_time:.1f} секунд")
                    
                    # Отображение результатов
                    st.success(f"Найдено {len(results)} вариантов параметров!")
                    
                    # Топ-10 результатов
                    st.subheader("🏆 Топ-10 лучших параметров")
                    
                    top_results = results[:10]
                    results_data = []
                    
                    for i, result in enumerate(top_results):
                        results_data.append({
                            'Ранг': i + 1,
                            'Общий скор (%)': f"{result.combined_score:.2f}",
                            'Бэктест (%)': f"{result.backtest_score:.2f}",
                            'Форвард (%)': f"{result.forward_score:.2f}",
                            'Диапазон сетки (%)': f"{result.params.grid_range_pct:.1f}",
                            'Шаг сетки (%)': f"{result.params.grid_step_pct:.2f}",
                            'Стоп-лосс (%)': f"{result.params.stop_loss_pct:.1f}",
                            'Сделок': result.trades_count,
                            'Просадка (%)': f"{result.drawdown:.2f}"
                        })
                    
                    results_df = pd.DataFrame(results_data)
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Детальная информация о лучшем результате
                    if results:
                        best_result = results[0]
                        st.subheader("🥇 Лучший результат")
                        
                        col_info1, col_info2, col_info3 = st.columns(3)
                        
                        with col_info1:
                            st.metric("Комбинированный скор", f"{best_result.combined_score:.2f}%")
                            st.metric("Диапазон сетки", f"{best_result.params.grid_range_pct:.1f}%")
                        
                        with col_info2:
                            st.metric("Бэктест vs Форвард", 
                                    f"{best_result.backtest_score:.2f}% vs {best_result.forward_score:.2f}%")
                            st.metric("Шаг сетки", f"{best_result.params.grid_step_pct:.2f}%")
                        
                        with col_info3:
                            st.metric("Всего сделок", best_result.trades_count)
                            st.metric("Стоп-лосс", f"{best_result.params.stop_loss_pct:.1f}%")
                        
                        # Анализ стабильности
                        stability = abs(best_result.backtest_score - best_result.forward_score)
                        if stability < 5:
                            st.success(f"🟢 Высокая стабильность (разность {stability:.2f}%)")
                        elif stability < 10:
                            st.warning(f"🟡 Средняя стабильность (разность {stability:.2f}%)")
                        else:
                            st.error(f"🔴 Низкая стабильность (разность {stability:.2f}%)")
                        
                        # Кнопка для тестирования лучших параметров
                        st.subheader("🧪 Тестирование лучших параметров")
                        
                        if st.button("🔬 Протестировать лучшие параметры на полных данных"):
                            with st.spinner("Тестирование..."):
                                test_stats_long, test_stats_short, test_log_long, test_log_short = grid_analyzer.estimate_dual_grid_by_candles_realistic(
                                    df=df_opt,
                                    initial_balance_long=opt_balance,
                                    initial_balance_short=opt_balance,
                                    grid_range_pct=best_result.params.grid_range_pct,
                                    grid_step_pct=best_result.params.grid_step_pct,
                                    order_size_usd_long=0,
                                    order_size_usd_short=0,
                                    commission_pct=TAKER_COMMISSION_RATE * 100,
                                    stop_loss_pct=best_result.params.stop_loss_pct if best_result.params.stop_loss_pct > 0 else None,
                                    debug=False
                                )
                                
                                total_pnl = test_stats_long['total_pnl'] + test_stats_short['total_pnl']
                                total_pnl_pct = (total_pnl / (opt_balance * 2)) * 100
                                
                                st.success("✅ Тест на полных данных завершен!")
                                st.metric("Результат на полных данных", f"{total_pnl_pct:.2f}%", f"${total_pnl:.2f}")
                                
                                # Сравнение с ожидаемым результатом
                                expected_avg = (best_result.backtest_score + best_result.forward_score) / 2
                                difference = total_pnl_pct - expected_avg
                                st.info(f"Отклонение от ожидаемого: {difference:.2f}%")
                    
            except Exception as e:
                st.error(f"Ошибка во время оптимизации: {e}")
                st.exception(e)

# Основной блок запуска анализа (если кнопка нажата)
if start_analysis:
    with log_container:
        if not api_key or not api_secret:
            st.error("❌ Введите API ключи для начала анализа.")
        else:
            # Прогресс анализа
            progress_analysis = st.progress(0)
            status_analysis = st.empty()
            
            try:
                
                # Инициализация классов
                status_analysis.info("🔧 Инициализация модулей...")
                progress_analysis.progress(10)
                
                collector = BinanceDataCollector(api_key, api_secret)
                processor = DataProcessor(collector)
                analyzer = CorrelationAnalyzer(collector) # Исправлено: передаем collector
                portfolio_builder = PortfolioBuilder(collector, analyzer) # Исправлено: передаем collector и analyzer
                
                progress_analysis.progress(30)
                
                # Получение и фильтрация пар
                status_analysis.info("📊 Получение и фильтрация торговых пар...")
                all_pairs = collector.get_all_usdt_pairs()
                filtered_pairs = processor.filter_pairs_by_volume_and_price(
                    all_pairs, 
                    min_volume=min_volume, 
                    min_price=min_price, 
                    max_price=max_price
                )
                
                progress_analysis.progress(70)
                
                # Ограничиваем количество пар для анализа
                pairs_to_analyze = filtered_pairs[:max_pairs]
                
                progress_analysis.progress(90)
                status_analysis.success(f"✅ Отобрано {len(pairs_to_analyze)} пар для анализа.")
                
                # Сохраняем результаты фильтрации в session_state
                st.session_state.filtered_pairs = pairs_to_analyze
                
                progress_analysis.progress(100)
                
                # Обновляем вкладку 2 с отфильтрованными парами
                st.success("🎉 Анализ завершен! Переключитесь на вкладку 'Фильтр торговых пар' для просмотра результатов.")
                
                # Автоматически показываем результаты
                st.subheader("📋 Результаты фильтрации")
                
                col_res1, col_res2, col_res3 = st.columns(3)
                with col_res1:
                    st.metric("Всего пар USDT", len(all_pairs))
                with col_res2:
                    st.metric("Прошли фильтр", len(filtered_pairs))
                with col_res3:
                    st.metric("Выбрано для анализа", len(pairs_to_analyze))
                
                pairs_df = pd.DataFrame({
                    'Символ': pairs_to_analyze,
                    'Описание': [f"Торговая пара {p}" for p in pairs_to_analyze],
                    'Статус': ['✅ Готов к Grid Trading'] * len(pairs_to_analyze)
                })
                st.dataframe(pairs_df, use_container_width=True)
                
                # Кнопка для сохранения отфильтрованного списка
                if st.button("💾 Сохранить отфильтрованный список как основной"):
                    st.session_state.saved_pairs = pairs_to_analyze
                    save_pairs_list(pairs_to_analyze)
                    st.success("Отфильтрованный список сохранен как основной!")
                
            except Exception as e:
                status_analysis.error(f"❌ Произошла ошибка: {str(e)}")
                st.exception(e) # Выводим полный traceback для отладки
