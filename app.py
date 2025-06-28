"""
Простой веб-интерфейс для анализа и отбора торговых пар Binance с использованием Streamlit.
"""

import os
import time
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Для headless окружения (Railway, Heroku и т.д.)
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

def get_api_keys_source() -> str:
    """Определяет источник загрузки API ключей используя кэшированную информацию"""
    if 'api_keys_source' in st.session_state:
        return st.session_state.api_keys_source
    
    # Если кэша нет, используем резервную логику без дополнительных запросов
    try:
        # Проверяем Streamlit secrets
        try:
            if hasattr(st, 'secrets') and 'binance' in st.secrets:
                return "Streamlit Secrets"
        except Exception:
            pass
        
        # Проверяем переменные окружения
        if os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_API_SECRET"):
            return "Переменные окружения"
        
        # Проверяем локальный файл (без запроса в GitHub для экономии времени)
        if os.path.exists("config.json"):
            return "Локальный config.json"
        
        return "Не найдены"
    except Exception:
        return "Ошибка определения"

def load_api_keys() -> Tuple[str, str]:
    """Загружает API ключи из различных источников в порядке приоритета (с кэшированием)"""
    # Проверяем кэш в session_state
    if 'cached_api_key' in st.session_state and 'cached_api_secret' in st.session_state:
        cached_key = st.session_state.cached_api_key
        cached_secret = st.session_state.cached_api_secret
        if cached_key and cached_secret:
            return cached_key, cached_secret
    
    try:
        api_key = ""
        api_secret = ""
        source = ""
        
        # 1. Сначала пробуем загрузить из Streamlit secrets (для Streamlit Cloud)
        try:
            if hasattr(st, 'secrets') and 'binance' in st.secrets:
                api_key = st.secrets["binance"]["api_key"]
                api_secret = st.secrets["binance"]["api_secret"]
                source = "Streamlit Secrets"
        except Exception:
            pass  # Игнорируем ошибки со secrets
        
        # 2. Затем из переменных окружения (для Heroku, Railway, Render)
        if not api_key or not api_secret:
            env_api_key = os.getenv("BINANCE_API_KEY")
            env_api_secret = os.getenv("BINANCE_API_SECRET")
            if env_api_key and env_api_secret:
                api_key = env_api_key
                api_secret = env_api_secret
                source = "переменных окружения"
        
        # 3. Для локального запуска - из GitHub репозитория
        if not api_key or not api_secret:
            try:
                github_url = "https://raw.githubusercontent.com/demetrius2017/binance_correlation_for_grids_trading/main/config.json"
                response = requests.get(github_url, timeout=10)
                if response.status_code == 200:
                    github_config = response.json()
                    github_api_key = github_config.get("api_key", "")
                    github_api_secret = github_config.get("api_secret", "")
                    if github_api_key and github_api_secret:
                        api_key = github_api_key
                        api_secret = github_api_secret
                        source = "GitHub репозитория"
            except Exception as github_error:
                pass  # Игнорируем ошибки с GitHub
        
        # 4. Наконец из локального файла config.json (резервный вариант)
        if not api_key or not api_secret:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                local_api_key = config.get("api_key", "")
                local_api_secret = config.get("api_secret", "")
                if local_api_key and local_api_secret:
                    api_key = local_api_key
                    api_secret = local_api_secret
                    source = "локального config.json"
        
        # Кэшируем результат и выводим сообщение только при первой загрузке
        if api_key and api_secret:
            # Проверяем, изменились ли ключи
            if ('cached_api_key' not in st.session_state or 
                st.session_state.cached_api_key != api_key or
                st.session_state.cached_api_secret != api_secret):
                
                st.session_state.cached_api_key = api_key
                st.session_state.cached_api_secret = api_secret
                st.session_state.api_keys_source = source
                print(f"✅ API ключи загружены из {source}")
            
            return api_key, api_secret
        
        return "", ""
    except Exception as e:
        print(f"❌ Ошибка при загрузке API ключей: {e}")
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

if 'filtered_pairs' not in st.session_state:
    st.session_state.filtered_pairs = []

# Результаты Grid Trading
if 'grid_simulation_results' not in st.session_state:
    st.session_state.grid_simulation_results = None

if 'grid_simulation_params' not in st.session_state:
    st.session_state.grid_simulation_params = None

# Результаты оптимизации
if 'optimization_results' not in st.session_state:
    st.session_state.optimization_results = None

if 'optimization_params' not in st.session_state:
    st.session_state.optimization_params = None

if 'optimization_best_result' not in st.session_state:
    st.session_state.optimization_best_result = None

# Переменная для переноса параметров из оптимизации в Grid Trading
if 'transfer_params' not in st.session_state:
    st.session_state.transfer_params = None

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
    
    # Показываем статус сохранения ключей с источником
    keys_source = get_api_keys_source()
    if st.session_state.api_keys_saved or (api_key and api_secret):
        st.success(f"✅ API ключи настроены")
        if keys_source != "Не найдены":
            st.info(f"📡 Источник: {keys_source}")
    elif not api_key and not api_secret:
        st.warning("⚠️ Введите API ключи для работы с Binance")
        if keys_source != "Не найдены":
            st.info(f"🔍 Обнаружены ключи в: {keys_source}")
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

# Загружаем сохраненные ключи для использования в других вкладках
saved_api_key, saved_api_secret = load_api_keys()

# Создаем вкладки (всегда доступны)
tab1, tab2, tab3, tab4 = st.tabs([
    "⚙️ Настройки", 
    "ℹ️ Информация",
    "⚡ Grid Trading",
    "🤖 Авто-оптимизация"
])

# Добавляем улучшенные стили для вкладок (поддержка светлой и темной темы)
st.markdown("""
<style>
/* Стили для вкладок - универсальные для светлой и темной темы */
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 14px;
    font-weight: bold;
    color: inherit;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    margin-bottom: 1rem;
}

.stTabs [data-baseweb="tab-list"] button {
    height: 50px;
    white-space: pre-wrap;
    border-radius: 8px 8px 0px 0px;
    gap: 4px;
    padding: 10px 16px;
    border: 2px solid transparent;
    transition: all 0.3s ease;
    font-weight: 600;
}

/* Светлая тема */
@media (prefers-color-scheme: light) {
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #f8f9fa;
        color: #495057;
        border-color: #dee2e6;
    }
    
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #e9ecef;
        color: #212529;
        border-color: #adb5bd;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
        box-shadow: 0 4px 8px rgba(255, 75, 75, 0.3);
    }
}

/* Темная тема */
@media (prefers-color-scheme: dark) {
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #2d3748;
        color: #e2e8f0;
        border-color: #4a5568;
    }
    
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #4a5568;
        color: #f7fafc;
        border-color: #718096;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
        box-shadow: 0 4px 8px rgba(255, 75, 75, 0.4);
    }
}

/* Принудительные стили для темной темы Streamlit */
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button {
    background-color: #2d3748 !important;
    color: #e2e8f0 !important;
    border-color: #4a5568 !important;
}

[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button:hover {
    background-color: #4a5568 !important;
    color: #f7fafc !important;
    border-color: #718096 !important;
}

[data-theme="dark"] .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background-color: #ff4b4b !important;
    color: white !important;
    border-color: #ff4b4b !important;
    box-shadow: 0 4px 8px rgba(255, 75, 75, 0.4) !important;
}

/* Дополнительная защита от засвеченности */
.stTabs [data-baseweb="tab-list"] button {
    opacity: 0.9;
}

.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)

# Предопределенный список популярных пар (для справки, больше не используется)

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
        st.success("📋 Binance API активен")
    
    with col_status3:
        if st.session_state.api_keys_saved:
            st.success("💾 Настройки сохранены")
        else:
            st.info("💾 Настройки не сохранены")
    
    st.markdown("---")
    
    # Основные параметры анализа с ползунками
    st.subheader("� Параметры фильтрации пар")
    
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
    
    # Отображение отфильтрованных пар из Binance
    st.subheader("🔍 Фильтрованные торговые пары")
    
    if api_key and api_secret:
        with st.spinner("Загрузка всех пар с Binance..."):
            try:
                collector = BinanceDataCollector(api_key, api_secret)
                processor = DataProcessor(collector)
                
                # Получаем и фильтруем все пары напрямую с Binance
                all_pairs = collector.get_all_usdt_pairs()
                filtered_pairs = processor.filter_pairs_by_volume_and_price(
                    all_pairs, 
                    min_volume=min_volume_calc, 
                    min_price=min_price_slider, 
                    max_price=max_price_slider
                )
                
                # Ограничиваем количество отображаемых пар
                display_pairs = filtered_pairs[:max_pairs_slider]
                
                # Сохраняем в session_state для использования в других вкладках
                st.session_state.filtered_pairs = display_pairs
                
                # Отображаем результаты
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.metric("Всего пар USDT", len(all_pairs))
                with col_info2:
                    st.metric("Прошли фильтр", len(filtered_pairs))
                with col_info3:
                    st.metric("Отображено", len(display_pairs))
                
                pairs_df = pd.DataFrame({
                    'Символ': display_pairs,
                    'Статус': ['✅ Готов к анализу'] * len(display_pairs)
                })
                
                st.dataframe(pairs_df, use_container_width=True)
                
                if len(filtered_pairs) > max_pairs_slider:
                    st.info(f"Показано {max_pairs_slider} из {len(filtered_pairs)} отфильтрованных пар. Увеличьте лимит для отображения большего количества.")
                    
            except Exception as e:
                st.error(f"Ошибка при загрузке пар: {e}")
                st.session_state.filtered_pairs = []
    else:
        st.warning("⚠️ Введите API ключи для загрузки списка торговых пар")
        st.session_state.filtered_pairs = []

# Вкладка 2: Информация
with tab2:
    st.header("🔍 Фильтр торговых пар")
    
# Все старые вкладки удалены, теперь используем только 4 вкладки

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
        3. **Просмотрите отфильтрованные пары** в той же вкладке
        4. **Протестируйте Grid Trading** во вкладке "Grid Trading"
        5. **Оптимизируйте параметры** во вкладке "Авто-оптимизация"
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

# Вкладка 3: Grid Trading (всегда доступна)
with tab3:
    st.header("⚡ Симуляция сеточной торговли")
    
    # Проверяем, есть ли переданные параметры из оптимизации
    if st.session_state.transfer_params is not None:
        transferred = st.session_state.transfer_params
        st.success(f"""
        🎯 **Параметры загружены из:** {transferred['source']}
        
        • **Пара**: {transferred['pair']}
        • **Диапазон сетки**: {transferred['grid_range_pct']:.1f}%
        • **Шаг сетки**: {transferred['grid_step_pct']:.2f}%
        • **Стоп-лосс**: {transferred['stop_loss_pct']:.1f}%
        • **Баланс**: {transferred['initial_balance']} USDT
        • **Таймфрейм**: {transferred['timeframe']}
        • **Период**: {transferred['simulation_days']} дней
        """)
        
        col_clear, col_use = st.columns(2)
        with col_clear:
            if st.button("🗑️ Очистить загруженные параметры"):
                st.session_state.transfer_params = None
                st.rerun()
        with col_use:
            if st.button("✅ Использовать эти параметры", type="primary"):
                st.info("Параметры применены! Настройте дополнительные параметры ниже и запустите симуляцию.")
        
        st.markdown("---")

    # Параметры для сеточной торговли
    st.subheader("🎛️ Параметры сетки")
    
    col1, col2, col3 = st.columns(3)
    
    # Определяем значения по умолчанию из переданных параметров
    default_grid_range = st.session_state.transfer_params['grid_range_pct'] if st.session_state.transfer_params else 20.0
    default_grid_step = st.session_state.transfer_params['grid_step_pct'] if st.session_state.transfer_params else 1.0  
    default_balance = st.session_state.transfer_params['initial_balance'] if st.session_state.transfer_params else 1000
    
    with col1:
        grid_range_pct = st.slider(
            "Диапазон сетки (%)", 
            min_value=5.0, 
            max_value=50.0, 
            value=float(default_grid_range),
            step=1.0,
            help="Процентный диапазон для размещения сетки"
        )
    
    with col2:
        grid_step_pct = st.slider(
            "Шаг сетки (%)", 
            min_value=0.1, 
            max_value=5.0, 
            value=float(default_grid_step),
            step=0.1,
            key="grid_step_slider",
            help="Процентный шаг между уровнями сетки"
        )
        
    with col3:
        initial_balance = st.slider(
            "Начальный баланс (USDT)",
            min_value=100,
            max_value=50000,
            value=int(default_balance),
            step=100,
            help="Начальный капитал для симуляции"
        )

    st.markdown("---")
    
    # Дополнительные параметры симуляции
    st.subheader("⚙️ Дополнительные параметры")
    
    # Определяем значения по умолчанию из переданных параметров
    default_days = st.session_state.transfer_params['simulation_days'] if st.session_state.transfer_params else 90
    default_stop_loss = st.session_state.transfer_params['stop_loss_pct'] if st.session_state.transfer_params else 25.0
    default_timeframe = st.session_state.transfer_params['timeframe'] if st.session_state.transfer_params else "1h"
    default_timeframe_index = ["15m", "1h", "4h", "1d"].index(default_timeframe) if default_timeframe in ["15m", "1h", "4h", "1d"] else 1
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        simulation_days = st.slider(
            "Срок симуляции (дни)",
            min_value=7,
            max_value=365,
            value=int(default_days),
            step=1,
            help="Количество дней исторических данных для симуляции"
        )
    with col_b:
        stop_loss_pct = st.slider(
            "Стоп-лосс (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(default_stop_loss),
            step=2.5,
            help="Процент просадки для остановки торговли. 0 - отключить. Ускоряет тестирование плохих параметров."
        )
    with col_c:
        timeframe = st.selectbox(
            "Таймфрейм",
            options=["15m", "1h", "4h", "1d"],
            index=default_timeframe_index,
            help="Таймфрейм для загрузки исторических данных"
        )

    # Выбор пары для симуляции из отфильтрованных пар
    if 'filtered_pairs' in st.session_state and st.session_state.filtered_pairs:
        current_pairs_for_grid = st.session_state.filtered_pairs
    else:
        st.warning("⚠️ Сначала настройте фильтры в вкладке 'Настройки' для загрузки пар")
        current_pairs_for_grid = []
    
    if current_pairs_for_grid:
        # Определяем индекс выбранной пары из переданных параметров
        default_pair = st.session_state.transfer_params['pair'] if st.session_state.transfer_params else current_pairs_for_grid[0]
        try:
            default_pair_index = current_pairs_for_grid.index(default_pair) if default_pair in current_pairs_for_grid else 0
        except (ValueError, IndexError):
            default_pair_index = 0
            
        selected_pair_for_grid = st.selectbox(
            "Выберите пару для симуляции",
            current_pairs_for_grid,
            index=default_pair_index,
            key="selected_pair_for_grid",
            help=f"Доступно {len(current_pairs_for_grid)} отфильтрованных пар"
        )

        # Отображение сохраненных результатов Grid Trading
        if (st.session_state.grid_simulation_results is not None and 
            st.session_state.grid_simulation_params is not None):
            st.markdown("---")
            st.subheader("📈 Последние результаты симуляции")
            
            saved_results = st.session_state.grid_simulation_results
            saved_params = st.session_state.grid_simulation_params
            
            # Информация о последнем тесте
            st.info(f"""
            **Последний тест**: {saved_results['pair']} 
            **Время**: {saved_results['timestamp']}
            **Параметры**: Диапазон {saved_params['grid_range_pct']}%, Шаг {saved_params['grid_step_pct']}%, Стоп-лосс {saved_params['stop_loss_pct']}%
            """)
            
            # Краткие результаты
            stats_long = saved_results['stats_long']
            stats_short = saved_results['stats_short']
            total_pnl = stats_long['total_pnl'] + stats_short['total_pnl']
            total_initial_balance = saved_params['initial_balance'] * 2
            total_pnl_pct = (total_pnl / total_initial_balance) * 100 if total_initial_balance > 0 else 0
            total_trades = stats_long['trades_count'] + stats_short['trades_count']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PnL", f"${total_pnl:.2f}", f"{total_pnl_pct:.2f}%")
            with col2:
                st.metric("Сделок", total_trades)
            with col3:
                avg_dd = (stats_long.get('max_drawdown_pct', 0) + stats_short.get('max_drawdown_pct', 0)) / 2
                st.metric("Макс. DD", f"{avg_dd:.2f}%")
            with col4:
                total_stop_loss_triggers = stats_long.get('stop_loss_triggers', 0) + stats_short.get('stop_loss_triggers', 0)
                st.metric("Стоп-лоссов", total_stop_loss_triggers)
            
            # Развернутые результаты в expander
            with st.expander("🔍 Детальные результаты"):
                # Расчет всех метрик
                total_commission = stats_long['total_commission'] + stats_short['total_commission']
                avg_sharpe = (stats_long.get('sharpe_ratio', 0) + stats_short.get('sharpe_ratio', 0)) / 2
                avg_pf = (stats_long.get('profit_factor', 0) + stats_short.get('profit_factor', 0)) / 2
                
                # Детальная статистика
                results_data = {
                    "Метрика": ["Баланс Long", "PnL Long ($)", "PnL Long (%)", "Сделок Long", "Комиссии Long ($)", "Стоп-лоссов Long",
                                "Баланс Short", "PnL Short ($)", "PnL Short (%)", "Сделок Short", "Комиссии Short ($)", "Стоп-лоссов Short"],
                    "Значение": [
                        f"${stats_long['final_balance']:.2f}", f"${stats_long['total_pnl']:.2f}", f"{stats_long['total_pnl_pct']:.2f}%", str(stats_long['trades_count']), f"${stats_long['total_commission']:.2f}", str(stats_long.get('stop_loss_triggers', 0)),
                        f"${stats_short['final_balance']:.2f}", f"${stats_short['total_pnl']:.2f}", f"{stats_short['total_pnl_pct']:.2f}%", str(stats_short['trades_count']), f"${stats_short['total_commission']:.2f}", str(stats_short.get('stop_loss_triggers', 0))
                    ]
                }
                results_df = pd.DataFrame(results_data)
                results_df['Значение'] = results_df['Значение'].astype(str)
                st.dataframe(results_df, use_container_width=True)
                
                # Логи сделок
                if saved_results['log_long_df']:
                    st.subheader("Лог сделок Long")
                    df_long = pd.DataFrame(saved_results['log_long_df'])
                    st.dataframe(df_long, use_container_width=True)
                
                if saved_results['log_short_df']:
                    st.subheader("Лог сделок Short")
                    df_short = pd.DataFrame(saved_results['log_short_df'])
                    st.dataframe(df_short, use_container_width=True)
            
            st.markdown("---")

        # Кнопки управления
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
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
                            # Используем правильный вызов с количеством дней
                            df_for_simulation = collector.get_historical_data(selected_pair_for_grid, timeframe, simulation_days)
                        
                        if df_for_simulation.empty:
                            st.error("Не удалось загрузить данные для симуляции.")
                        else:
                            # Отладочная информация
                            st.info(f"🔧 **Параметры симуляции:** Диапазон {grid_range_pct}%, Шаг {grid_step_pct}%, Баланс {initial_balance} USDT, Стоп-лосс {stop_loss_pct}%")
                            
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
                                    stop_loss_pct=stop_loss_pct if stop_loss_pct > 0 else None,  # Правильный стоп-лосс
                                    stop_loss_strategy='reset_grid',  # Перестраиваем сетку при стоп-лоссе
                                    max_drawdown_pct=None,  # DD только для информации
                                    debug=False
                                )

                            st.success(f"✅ Симуляция для {selected_pair_for_grid} за {simulation_days} дней завершена!")
                            
                            # Сохранение результатов в session_state
                            st.session_state.grid_simulation_results = {
                                'pair': selected_pair_for_grid,
                                'stats_long': stats_long,
                                'stats_short': stats_short,
                                'log_long_df': log_long_df,
                                'log_short_df': log_short_df,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            st.session_state.grid_simulation_params = {
                                'grid_range_pct': grid_range_pct,
                                'grid_step_pct': grid_step_pct,
                                'initial_balance': initial_balance,
                                'simulation_days': simulation_days,
                                'stop_loss_pct': stop_loss_pct,
                                'timeframe': timeframe
                            }
                            
                            # Отображение результатов
                            st.subheader("📊 Результаты симуляции")
                            
                            # Расчет комбинированных результатов
                            total_pnl = stats_long['total_pnl'] + stats_short['total_pnl']
                            total_initial_balance = initial_balance * 2
                            total_pnl_pct = (total_pnl / total_initial_balance) * 100 if total_initial_balance > 0 else 0
                            total_trades = stats_long['trades_count'] + stats_short['trades_count']
                            total_commission = stats_long['total_commission'] + stats_short['total_commission']
                            
                            # Продвинутые метрики
                            avg_dd = (stats_long.get('max_drawdown_pct', 0) + stats_short.get('max_drawdown_pct', 0)) / 2
                            avg_sharpe = (stats_long.get('sharpe_ratio', 0) + stats_short.get('sharpe_ratio', 0)) / 2
                            avg_pf = (stats_long.get('profit_factor', 0) + stats_short.get('profit_factor', 0)) / 2
                            
                            col_result1, col_result2, col_result3, col_result4, col_result5 = st.columns(5)
                            
                            with col_result1:
                                st.metric("Общий PnL", f"${total_pnl:.2f}", f"{total_pnl_pct:.2f}%")
                            with col_result2:
                                st.metric("Всего сделок", total_trades)
                            with col_result3:
                                st.metric("Макс. просадка", f"{avg_dd:.2f}%")
                            with col_result4:
                                st.metric("Коэфф. Шарпа", f"{avg_sharpe:.2f}")
                            with col_result5:
                                total_stop_loss_triggers = stats_long.get('stop_loss_triggers', 0) + stats_short.get('stop_loss_triggers', 0)
                                st.metric("Срабатываний стоп-лосса", total_stop_loss_triggers)
                            
                            # Дополнительная информация о стоп-лоссах
                            if total_stop_loss_triggers > 0:
                                st.warning(f"⚠️ Сетка перестраивалась {total_stop_loss_triggers} раз(а) при срабатывании стоп-лосса {stop_loss_pct}%")
                            
                            # Карточка с краткой сводкой
                            st.info(f"""
                            **📋 Краткая сводка:**
                            • **PnL**: ${total_pnl:.2f} ({total_pnl_pct:.2f}%) 
                            • **Сделок**: {total_trades} | **Комиссии**: ${total_commission:.2f}
                            • **DD**: {avg_dd:.2f}% | **Sharpe**: {avg_sharpe:.2f} | **PF**: {avg_pf:.1f}
                            • **Стоп-лоссов**: {total_stop_loss_triggers} ({stats_long.get('stop_loss_triggers', 0)} Long + {stats_short.get('stop_loss_triggers', 0)} Short)
                            """)

                            st.subheader("📋 Детальная статистика")
                            
                            results_data = {
                                "Метрика": ["Баланс Long", "PnL Long ($)", "PnL Long (%)", "Сделок Long", "Комиссии Long ($)", "Стоп-лоссов Long",
                                            "Баланс Short", "PnL Short ($)", "PnL Short (%)", "Сделок Short", "Комиссии Short ($)", "Стоп-лоссов Short"],
                                "Значение": [
                                    f"${stats_long['final_balance']:.2f}", f"${stats_long['total_pnl']:.2f}", f"{stats_long['total_pnl_pct']:.2f}%", str(stats_long['trades_count']), f"${stats_long['total_commission']:.2f}", str(stats_long.get('stop_loss_triggers', 0)),
                                    f"${stats_short['final_balance']:.2f}", f"${stats_short['total_pnl']:.2f}", f"{stats_short['total_pnl_pct']:.2f}%", str(stats_short['trades_count']), f"${stats_short['total_commission']:.2f}", str(stats_short.get('stop_loss_triggers', 0))
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
        
        with col_btn2:
            if st.session_state.grid_simulation_results is not None:
                if st.button("🗑️ Очистить результаты", key="clear_grid_results"):
                    st.session_state.grid_simulation_results = None
                    st.session_state.grid_simulation_params = None
                    st.rerun()
    else:
        st.info("Загрузите список торговых пар в вкладке 'Настройки'")

# Вкладка 4: Авто-оптимизация
with tab4:
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
        # Используем отфильтрованные пары из первой вкладки
        if 'filtered_pairs' in st.session_state and st.session_state.filtered_pairs:
            current_pairs_for_opt = st.session_state.filtered_pairs
        else:
            st.warning("⚠️ Сначала настройте фильтры в вкладке 'Настройки' для загрузки пар")
            current_pairs_for_opt = []
        
        if current_pairs_for_opt:
            opt_pair = st.selectbox(
                "Пара для оптимизации",
                current_pairs_for_opt,
                key="opt_pair",
                help=f"Доступно {len(current_pairs_for_opt)} отфильтрованных пар"
            )
        else:
            st.info("Загрузите список торговых пар в вкладке 'Настройки'")
            opt_pair = None
        
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
    
    # Настройки риск-менеджмента
    st.subheader("🛡️ Настройки тестирования")
    col_risk1, col_risk2 = st.columns(2)
    
    with col_risk1:
        forward_test_pct = st.slider(
            "Форвард тест (%)",
            min_value=0.2,
            max_value=0.5,
            value=0.3,
            step=0.05,
            help="Процент данных для форвард теста (проверки на новых данных)"
        )
    
    with col_risk2:
        st.info("""
        **Только стоп-лосс используется как ограничитель**
        
        Drawdown показывается информативно в результатах для оценки качества стратегии.
        """)
    
    st.markdown("---")
    
    # Отображение сохраненных результатов оптимизации
    if (st.session_state.optimization_results is not None and 
        st.session_state.optimization_params is not None):
        st.subheader("🎯 Последние результаты оптимизации")
        
        opt_params = st.session_state.optimization_params
        opt_results = st.session_state.optimization_results
        best_result = st.session_state.optimization_best_result
        
        # Информация о последней оптимизации
        st.info(f"""
        **Пара**: {opt_params['pair']} | **Метод**: {opt_params['method']}  
        **Время**: {opt_params['timestamp']} | **Длительность**: {opt_params['duration_seconds']:.1f}с
        **Найдено вариантов**: {len(opt_results)} | **Данные**: {opt_params['days']} дней, {opt_params['timeframe']}
        """)
        
        if best_result:
            # Лучший результат
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Лучший скор", f"{best_result.combined_score:.2f}%")
            with col2:
                st.metric("Бэктест / Форвард", f"{best_result.backtest_score:.2f}% / {best_result.forward_score:.2f}%")
            with col3:
                st.metric("Drawdown", f"{best_result.max_drawdown_pct:.2f}%")
            with col4:
                st.metric("Sharpe", f"{best_result.sharpe_ratio:.2f}")
            
            # Параметры лучшего результата
            st.success(f"""
            **🏆 Лучшие параметры:**
            • **Диапазон сетки**: {best_result.params.grid_range_pct:.1f}%
            • **Шаг сетки**: {best_result.params.grid_step_pct:.2f}%  
            • **Стоп-лосс**: {best_result.params.stop_loss_pct:.1f}%
            • **Сделок**: {best_result.trades_count} | **PF**: {best_result.profit_factor:.1f}
            """)
            
            # Топ-5 результатов в expander
            with st.expander("🔍 Топ-5 результатов"):
                top_5 = opt_results[:5]
                results_data = []
                
                for i, result in enumerate(top_5):
                    stability = abs(result.backtest_score - result.forward_score)
                    dd_pct = result.max_drawdown_pct
                    sharpe = result.sharpe_ratio
                    
                    if dd_pct < 10 and sharpe > 1.0 and stability < 5:
                        quality_indicator = "🟢"
                    elif dd_pct < 20 and sharpe > 0.5 and stability < 10:
                        quality_indicator = "🟡"
                    else:
                        quality_indicator = "🔴"
                    
                    results_data.append({
                        'Ранг': f"{quality_indicator} {i + 1}",
                        'Скор (%)': f"{result.combined_score:.2f}",
                        'Бэктест (%)': f"{result.backtest_score:.2f}",
                        'Форвард (%)': f"{result.forward_score:.2f}",
                        'DD (%)': f"{result.max_drawdown_pct:.2f}",
                        'Sharpe': f"{result.sharpe_ratio:.2f}",
                        'Диапазон (%)': f"{result.params.grid_range_pct:.1f}",
                        'Шаг (%)': f"{result.params.grid_step_pct:.2f}",
                        'Стоп-лосс (%)': f"{result.params.stop_loss_pct:.1f}"
                    })
                
                results_df = pd.DataFrame(results_data)
                st.dataframe(results_df, use_container_width=True)
                
                # Добавляем кнопки "Тест" для топ-5 результатов
                st.write("**Быстрый тест параметров:**")
                cols = st.columns(5)
                for i, result in enumerate(top_5):
                    with cols[i]:
                        rank = i + 1
                        if st.button(f"🧪 #{rank}", key=f"test_top5_btn_{i}"):
                            # Сохраняем параметры для переноса
                            st.session_state.transfer_params = {
                                'pair': st.session_state.optimization_params['pair'],
                                'grid_range_pct': result.params.grid_range_pct,
                                'grid_step_pct': result.params.grid_step_pct,
                                'stop_loss_pct': result.params.stop_loss_pct,
                                'initial_balance': st.session_state.optimization_params['balance'],
                                'timeframe': st.session_state.optimization_params['timeframe'],
                                'simulation_days': st.session_state.optimization_params['days'],
                                'source': f"Топ-5 #{rank} (скор: {result.combined_score:.2f}%)"
                            }
                            st.success(f"✅ Параметры #{rank} готовы к тесту!")
                            
            # Кнопка "Тест" для лучшего результата
            if st.button("🏆 Тестировать лучший результат", type="primary"):
                # Сохраняем параметры лучшего результата для переноса
                st.session_state.transfer_params = {
                    'pair': st.session_state.optimization_params['pair'],
                    'grid_range_pct': best_result.params.grid_range_pct,
                    'grid_step_pct': best_result.params.grid_step_pct,
                    'stop_loss_pct': best_result.params.stop_loss_pct,
                    'initial_balance': st.session_state.optimization_params['balance'],
                    'timeframe': st.session_state.optimization_params['timeframe'],
                    'simulation_days': st.session_state.optimization_params['days'],
                    'source': f"Лучший результат (скор: {best_result.combined_score:.2f}%)"
                }
                st.success("🏆 Лучшие параметры готовы! Перейдите во вкладку Grid Trading для тестирования.")
                st.balloons()
        
        st.markdown("---")
    
    # Кнопки управления оптимизацией
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        if st.button("🚀 Запустить оптимизацию", type="primary", key="start_optimization"):
            # Исправляем проблему с API ключами - используем загруженные ключи
            if not api_key or not api_secret:
                st.error("Пожалуйста, введите API ключи в боковой панели.")
            elif not opt_pair:
                st.error("Пожалуйста, сначала загрузите пары в вкладке 'Настройки'.")
            else:
                try:
                    # Прогресс бар и контейнеры для вывода
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Инициализация с правильными API ключами
                    status_text.text("Инициализация...")
                    collector = BinanceDataCollector(api_key, api_secret)  # Используем ключи из sidebar
                    grid_analyzer = GridAnalyzer(collector)
                    optimizer = GridOptimizer(grid_analyzer, TAKER_COMMISSION_RATE)
                    
                    # Загрузка данных
                    status_text.text(f"Загрузка данных для {opt_pair}...")
                    progress_bar.progress(10)
                    
                    # Используем правильный вызов с количеством дней
                    df_opt = collector.get_historical_data(opt_pair, opt_timeframe, opt_days)
                    
                    if df_opt.empty:
                        st.error("Не удалось загрузить данные для оптимизации.")
                        # Очистка предыдущих результатов при ошибке
                        st.session_state.optimization_results = None
                        st.session_state.optimization_params = None
                        st.session_state.optimization_best_result = None
                    else:
                        progress_bar.progress(20)
                        
                        # Функция для обновления прогресса (определяем заранее)
                        def progress_callback(message):
                            status_text.text(message)
                        
                        # Засекаем время начала (определяем заранее)
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
                                forward_test_pct=forward_test_pct,
                                max_workers=max_workers,
                                progress_callback=progress_callback
                            )
                        else:
                            status_text.text("Запуск адаптивного поиска...")
                            progress_bar.progress(30)
                            
                            results = optimizer.grid_search_adaptive(
                                df=df_opt,
                                initial_balance=opt_balance,
                                forward_test_pct=forward_test_pct,
                                iterations=iterations,
                                points_per_iteration=points_per_iteration,
                                progress_callback=progress_callback
                            )
                        
                        end_time = time.time()
                        progress_bar.progress(100)
                        status_text.text(f"✅ Оптимизация завершена за {end_time - start_time:.1f} секунд")
                        
                        # Сохранение результатов оптимизации в session_state
                        st.session_state.optimization_results = results
                        st.session_state.optimization_params = {
                            'pair': opt_pair,
                            'balance': opt_balance,
                            'timeframe': opt_timeframe,
                            'days': opt_days,
                            'method': opt_method,
                            'forward_test_pct': forward_test_pct,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'duration_seconds': end_time - start_time
                        }
                        if results:
                            st.session_state.optimization_best_result = results[0]
                        
                        # Отображение результатов
                        st.success(f"Найдено {len(results)} вариантов параметров!")
                        
                        # Топ-10 результатов
                        st.subheader("🏆 Топ-10 лучших параметров")
                        
                        top_results = results[:10]
                        results_data = []
                        
                        for i, result in enumerate(top_results):
                            # Цветовая индикация качества
                            stability = abs(result.backtest_score - result.forward_score)
                            dd_pct = result.max_drawdown_pct
                            sharpe = result.sharpe_ratio
                            
                            if dd_pct < 10 and sharpe > 1.0 and stability < 5:
                                quality_indicator = "🟢"
                            elif dd_pct < 20 and sharpe > 0.5 and stability < 10:
                                quality_indicator = "🟡"
                            else:
                                quality_indicator = "🔴"
                            
                            results_data.append({
                                'Ранг': f"{quality_indicator} {i + 1}",
                                'Общий скор (%)': f"{result.combined_score:.2f}",
                                'Бэктест (%)': f"{result.backtest_score:.2f}",
                                'Форвард (%)': f"{result.forward_score:.2f}",
                                'DD (%)': f"{result.max_drawdown_pct:.2f}",
                                'Sharpe': f"{result.sharpe_ratio:.2f}",
                                'PF': f"{result.profit_factor:.1f}",
                                'Диапазон сетки (%)': f"{result.params.grid_range_pct:.1f}",
                                'Шаг сетки (%)': f"{result.params.grid_step_pct:.2f}",
                                'Стоп-лосс (%)': f"{result.params.stop_loss_pct:.1f}",
                                'Сделок': result.trades_count
                            })
                        
                        results_df = pd.DataFrame(results_data)
                        
                        # Отображаем таблицу с кнопками "Тест"
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Добавляем кнопки "Тест" для каждого результата
                        st.subheader("🧪 Тестирование параметров")
                        st.write("Нажмите кнопку 'Тест' для переноса параметров во вкладку Grid Trading:")
                        
                        # Создаем колонки для кнопок
                        cols_per_row = 5
                        for i in range(0, min(10, len(top_results)), cols_per_row):
                            cols = st.columns(cols_per_row)
                            for j in range(cols_per_row):
                                idx = i + j
                                if idx < len(top_results):
                                    result = top_results[idx]
                                    with cols[j]:
                                        rank = idx + 1
                                        if st.button(f"🧪 Тест #{rank}", key=f"test_btn_{idx}"):
                                            # Сохраняем параметры для переноса
                                            st.session_state.transfer_params = {
                                                'pair': st.session_state.optimization_params['pair'],
                                                'grid_range_pct': result.params.grid_range_pct,
                                                'grid_step_pct': result.params.grid_step_pct,
                                                'stop_loss_pct': result.params.stop_loss_pct,
                                                'initial_balance': st.session_state.optimization_params['balance'],
                                                'timeframe': st.session_state.optimization_params['timeframe'],
                                                'simulation_days': st.session_state.optimization_params['days'],
                                                'source': f"Оптимизация #{rank} (скор: {result.combined_score:.2f}%)"
                                            }
                                            st.success(f"✅ Параметры #{rank} сохранены! Перейдите во вкладку Grid Trading для тестирования.")
                                            st.balloons()
                        
                        # Пояснения к новым метрикам
                        with st.expander("📚 Пояснения к метрикам"):
                            st.markdown("""
                            **Новые продвинутые метрики:**
                            - **DD (%)** - максимальная просадка (Draw Down) 
                            - **Sharpe** - коэффициент Шарпа (оценка эффективности с учетом риска)
                            - **PF** - Profit Factor (отношение суммы прибыли к сумме убытков)
                            
                            **Цветовая индикация качества:**
                            - 🟢 **Зеленый**: Отличные показатели (DD<10%, Sharpe>1.0, стабильность<5%)
                            - 🟡 **Желтый**: Хорошие показатели (DD<20%, Sharpe>0.5, стабильность<10%)  
                            - 🔴 **Красный**: Плохие показатели (DD>20%, Sharpe<0.5, стабильность>10%)
                            """)
                        
                        # Детальная информация о лучшем результате
                        if results:
                            best_result = results[0]
                            st.subheader("🥇 Лучший результат")
                            
                            # 4 колонки метрик как описано в отчете
                            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                            
                            with col_info1:
                                st.metric("Комбинированный скор", f"{best_result.combined_score:.2f}%")
                                st.metric("Диапазон сетки", f"{best_result.params.grid_range_pct:.1f}%")
                            
                            with col_info2:
                                st.metric("Бэктест vs Форвард", 
                                        f"{best_result.backtest_score:.2f}% vs {best_result.forward_score:.2f}%")
                                st.metric("Шаг сетки", f"{best_result.params.grid_step_pct:.2f}%")
                            
                            with col_info3:
                                st.metric("Просадка", f"{best_result.max_drawdown_pct:.2f}%")
                                st.metric("Коэфф. Шарпа", f"{best_result.sharpe_ratio:.2f}")
                            
                            with col_info4:
                                st.metric("Profit Factor", f"{best_result.profit_factor:.1f}")
                                st.metric("Стоп-лосс", f"{best_result.params.stop_loss_pct:.1f}%")
                            
                            # Карточка результатов в стиле отчета
                            st.info(f"""
                            • **Общий скор**: {best_result.combined_score:.2f}%
                            • **Бэктест**: {best_result.backtest_score:.2f}%  
                            • **Форвард**: {best_result.forward_score:.2f}%
                            • **DD**: {best_result.max_drawdown_pct:.2f}% | **Sharpe**: {best_result.sharpe_ratio:.2f}
                            • **PF**: {best_result.profit_factor:.1f} | **Сделок**: {best_result.trades_count}
                            """)
                            
                            # Анализ стабильности
                            stability = abs(best_result.backtest_score - best_result.forward_score)
                            dd_pct = best_result.max_drawdown_pct
                            sharpe = best_result.sharpe_ratio
                            
                            # Цветовая индикация качества согласно отчету
                            if dd_pct < 10 and sharpe > 1.0 and stability < 5:
                                st.success(f"🟢 **Отличные показатели**: DD<10%, Sharpe>1.0, стабильность<5%")
                            elif dd_pct < 20 and sharpe > 0.5 and stability < 10:
                                st.warning(f"🟡 **Хорошие показатели**: DD<20%, Sharpe>0.5, стабильность<10%")
                            else:
                                st.error(f"🔴 **Требует осторожности**: DD={dd_pct:.1f}%, Sharpe={sharpe:.2f}, нестабильность={stability:.1f}%")
                            
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
                                        max_drawdown_pct=None,  # На полных данных не ограничиваем DD
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
    
    with col_opt2:
        if st.session_state.optimization_results is not None:
            if st.button("🗑️ Очистить результаты оптимизации", key="clear_opt_results"):
                st.session_state.optimization_results = None
                st.session_state.optimization_params = None
                st.session_state.optimization_best_result = None
                st.rerun()

# Удаляем старый блок запуска анализа - теперь всё происходит в вкладке "Настройки"
