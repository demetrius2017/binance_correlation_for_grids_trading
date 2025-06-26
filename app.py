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

    # Выбор пары для симуляции из отфильтрованных пар
    if 'filtered_pairs' in st.session_state and st.session_state.filtered_pairs:
        current_pairs_for_grid = st.session_state.filtered_pairs
    else:
        st.warning("⚠️ Сначала настройте фильтры в вкладке 'Настройки' для загрузки пар")
        current_pairs_for_grid = []
    
    if current_pairs_for_grid:
        selected_pair_for_grid = st.selectbox(
            "Выберите пару для симуляции",
            current_pairs_for_grid,
            key="selected_pair_for_grid",
            help=f"Доступно {len(current_pairs_for_grid)} отфильтрованных пар"
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
    
    st.markdown("---")
    
    # Кнопка запуска оптимизации
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

# Удаляем старый блок запуска анализа - теперь всё происходит в вкладке "Настройки"
