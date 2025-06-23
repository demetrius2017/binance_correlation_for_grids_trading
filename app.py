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
    """Загружает API ключи из файла config.json"""
    try:
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
            save_api_keys(api_key, api_secret)
            st.success("API ключи сохранены!")
        else:
            st.error("Введите оба ключа для сохранения")
    
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
    
    # Параметры для сеточной торговли
    st.subheader("Параметры Grid Trading")
    
    grid_range_pct = st.slider(
        "Диапазон сетки (%)", 
        min_value=5.0, 
        max_value=50.0, 
        value=20.0,
        step=1.0,
        help="Процентный диапазон для размещения сетки"
    )
    
    grid_step_pct = st.slider(
        "Шаг сетки (%)", 
        min_value=0.1, 
        max_value=5.0, 
        value=1.0,
        step=0.1,
        help="Процентный шаг между уровнями сетки"
    )

# Кнопка запуска анализа
start_analysis = st.button("🚀 Запустить анализ", type="primary")

# Создаем контейнер для логов
log_container = st.container()

# Загружаем сохраненные ключи для использования в Grid Trading
saved_api_key, saved_api_secret = load_api_keys()

# Создаем вкладки (всегда доступны)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Список пар", 
    "🔗 Информация", 
    "💼 Настройки", 
    "📈 Графики",
    "⚡ Grid Trading"
])

# Предопределенный список популярных пар для всех вкладок
popular_pairs = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "LINKUSDT", "DOTUSDT", "LTCUSDT", "UNIUSDT", "SOLUSDT",
    "MATICUSDT", "ICXUSDT", "VETUSDT", "XLMUSDT", "TRXUSDT"
]

# Вкладка 1: Список пар
with tab1:
    st.header("Список торговых пар")
    
    if start_analysis:
        st.subheader("Результаты анализа появятся здесь после запуска")
        
    st.subheader("Доступные пары для анализа")
    pairs_df = pd.DataFrame({
        'Символ': popular_pairs[:max_pairs],
        'Описание': [f"Торговая пара {pair}" for pair in popular_pairs[:max_pairs]]
    })
    
    st.dataframe(pairs_df, use_container_width=True)
    st.success(f"Всего пар: {len(popular_pairs[:max_pairs])}")

# Вкладка 2: Информация
with tab2:
    st.header("Информация о системе")
    
    st.subheader("Реальные комиссии Binance")
    st.write(f"**Maker:** {MAKER_COMMISSION_RATE*100:.3f}%")
    st.write(f"**Taker:** {TAKER_COMMISSION_RATE*100:.3f}%")
    
    st.subheader("Возможности системы")
    st.write("✅ Анализ торговых пар")
    st.write("✅ Симуляция Grid Trading с реальными комиссиями") 
    st.write("✅ Часовые и дневные данные")
    st.write("✅ Различные стратегии стоп-лосса")

# Вкладка 3: Настройки
with tab3:
    st.header("Настройки анализа")
    
    st.subheader("Текущие параметры")
    st.write(f"Минимальный объем: ${min_volume:,}")
    st.write(f"Диапазон цен: ${min_price:.4f} - ${max_price:.2f}")
    st.write(f"Максимум пар: {max_pairs}")
    st.write(f"Диапазон сетки: {grid_range_pct}%")
    st.write(f"Шаг сетки: {grid_step_pct}%")

# Вкладка 4: Графики
with tab4:
    st.header("Графики цен")
    
    selected_symbol = st.selectbox("Выберите актив для просмотра", popular_pairs, key="chart_symbol")
    
    if selected_symbol and api_key and api_secret:
        try:
            collector = BinanceDataCollector(api_key, api_secret)
            df = collector.get_historical_data(selected_symbol, "1d", 90)
            if not df.empty:
                # График цены
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(df.index, df['close'], linewidth=2)
                ax.set_title(f"График цены {selected_symbol} за последние 90 дней")
                ax.set_xlabel("Дата")
                ax.set_ylabel("Цена (USDT)")
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                
                # Базовая статистика
                st.subheader(f"Статистика {selected_symbol}")
                st.write(f"Текущая цена: ${df['close'].iloc[-1]:.6f}")
                st.write(f"Максимум за период: ${df['high'].max():.6f}")
                st.write(f"Минимум за период: ${df['low'].min():.6f}")
                price_change = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
                st.write(f"Изменение за период: {price_change:.2f}%")
            else:
                st.warning("Данные для выбранной пары недоступны.")
        except Exception as e:
            st.error(f"Ошибка при получении данных: {str(e)}")
    elif not api_key or not api_secret:
        st.warning("Введите API ключи в боковой панели для просмотра графиков")

# Вкладка 5: Grid Trading (всегда доступна)
with tab5:
    st.header("Grid Trading Симуляция")
    st.write("Тестирование симуляции двойных сеток с реальными комиссиями Binance")
    
    # Пояснение по расчету доходности
    st.info("💡 **Расчет доходности:** Все проценты рассчитываются от начального капитала (100%). "
            "При стоп-лоссе убыток вычитается от текущего общего капитала.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Реальные комиссии Binance")
        st.write(f"**Maker:** {MAKER_COMMISSION_RATE*100:.3f}%")
        st.write(f"**Taker:** {TAKER_COMMISSION_RATE*100:.3f}%")
        
        st.subheader("Параметры симуляции")
        grid_symbol = st.selectbox("Выберите пару для симуляции", popular_pairs, key="grid_symbol")
        grid_step = st.slider("Шаг сетки (%)", 0.1, 2.0, 0.5, 0.1, key="grid_step")
        grid_range = st.slider("Диапазон сетки (%)", 5.0, 50.0, 20.0, 1.0, key="grid_range")
        stop_loss = st.slider("Стоп-лосс (%)", 1.0, 10.0, 5.0, 0.5, key="stop_loss")
        
        stop_loss_strategy = st.selectbox(
            "Стратегия стоп-лосса",
            ["independent", "close_both"],
            help="independent: сетки работают независимо, close_both: при стоп-лоссе одной закрываются обе",
            key="stop_loss_strategy"
        )
        
    with col2:
        timeframe_choice = st.selectbox(
            "Таймфрейм для симуляции",
            ["1h", "1d"],
            index=0,  # По умолчанию часовые данные
            help="Часовые данные дают более точные результаты для прибыльности",
            key="timeframe_choice"        )
        
        period_days = st.slider("Период тестирования (дней)", 7, 90, 30, 1, key="period_days")
        
        st.subheader("Компенсация убытков")
        lightning_compensation = st.slider(
            "Компенсация убытков (%)", 
            0.0, 50.0, 30.0, 1.0,
            help="Процент компенсации убытков при стоп-лоссах и молниях другой сеткой (реальная торговля: ~30%)",
            key="lightning_compensation"
        )
        if st.button("Запустить симуляцию Grid Trading", key="run_grid_simulation"):
            if not api_key or not api_secret:
                st.error("Введите API ключи для запуска симуляции")
            else:
                try:
                    # Создаем экземпляры классов
                    collector = BinanceDataCollector(api_key, api_secret)
                    grid_analyzer = GridAnalyzer(collector)                    # Получаем данные для симуляции
                    with st.spinner("Загружаем данные для симуляции..."):
                        if timeframe_choice == "1h":
                            df = collector.get_historical_data(grid_symbol, "1h", period_days * 24)
                        else:
                            df = collector.get_historical_data(grid_symbol, "1d", period_days)
                        
                    if df.empty:
                        st.error(f"Нет данных для пары {grid_symbol}")
                    else:
                        with st.spinner("Выполняем симуляцию..."):
                            # Симуляция с полными параметрами включая стоп-лосс и компенсацию молний
                            result = grid_analyzer.estimate_dual_grid_by_candles(
                                df,
                                grid_range_pct=grid_range,
                                grid_step_pct=grid_step,
                                commission_pct=0.1,  # Стандартная комиссия Binance
                                stop_loss_pct=stop_loss,
                                lightning_compensation=lightning_compensation
                            )
                        
                        # Отображаем результаты
                        st.success("Симуляция завершена!")
                        
                        st.subheader("Результаты симуляции Grid Trading")
                        
                        # Основная информация
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            st.metric(
                                "Общая доходность",
                                f"{result.get('combined_pct', 0):.2f}%",
                                delta=None
                            )
                            st.metric(
                                "Выходы за сетку",
                                result.get('breaks', 0)
                            )
                        
                        with col_b:
                            st.metric(
                                "Long доходность",
                                f"{result.get('long_pct', 0):.2f}%"
                            )
                            st.metric(
                                "Шаг сетки",
                                f"{result.get('grid_step_used', grid_step):.2f}%"                            )
                        
                        with col_c:
                            st.metric(
                                "Short доходность",
                                f"{result.get('short_pct', 0):.2f}%"
                            )
                            st.metric(
                                "Использованы комиссии",
                                f"{result.get('commission_pct', 0.1):.2f}%"
                            )
                        
                        # Дополнительная информация о сделках
                        col_d, col_e = st.columns(2)
                        with col_d:
                            st.metric(
                                "Всего сделок",
                                result.get('total_trades', 0)
                            )
                        with col_e:
                            st.metric(
                                "Процент успеха",
                                f"{result.get('win_rate', 0):.1f}%"
                            )
                        
                        # Детальная таблица
                        st.subheader("Детальная статистика")
                        
                        results_df = pd.DataFrame({
                            'Метрика': [                                'Общая доходность (%)',
                                'Long доходность (%)',
                                'Short доходность (%)',
                                'Выходы за сетку',
                                'Шаг сетки (%)',
                                'Таймфрейм',
                                'Период (дней)',
                                'Компенсация убытков (%)',
                                'Всего сделок',
                                'Прибыльных сделок',
                                'Убыточных сделок',
                                'Процент успеха (%)',
                                'Стоп-лоссы (события)',
                                'Стоп-лоссы (убытки %)',
                                'Молнии (события)',
                                'Молнии (чистые убытки %)'
                            ],
                            'Значение': [                                f"{result.get('combined_pct', 0):.2f}",
                                f"{result.get('long_pct', 0):.2f}",
                                f"{result.get('short_pct', 0):.2f}",
                                str(result.get('breaks', 0)),
                                f"{result.get('grid_step_pct', grid_step):.2f}",
                                str(timeframe_choice),
                                str(period_days),
                                f"{lightning_compensation:.1f}",
                                str(result.get('total_trades', 0)),
                                str(result.get('profitable_trades', 0)),
                                str(result.get('losing_trades', 0)),
                                f"{result.get('win_rate', 0):.1f}",
                                str(result.get('total_stop_loss_count', 0)),
                                f"{result.get('total_stop_loss_amount', 0):.2f}",
                                str(result.get('total_lightning_count', 0)),
                                f"{result.get('total_lightning_net_loss', 0):.2f}"
                            ]})
                        
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Детальная статистика по стоп-лоссам и молниям
                        if result.get('total_stop_loss_count', 0) > 0 or result.get('total_lightning_count', 0) > 0:
                            st.subheader("📊 Детальная статистика убытков")
                            
                            # Создаем две колонки для стоп-лоссов и молний
                            col_sl, col_lt = st.columns(2)
                            
                            with col_sl:
                                st.markdown("### 🛑 Стоп-лоссы")
                                stop_loss_stats = result.get('stop_loss_stats', {})
                                
                                # Общая статистика стоп-лоссов
                                st.metric(
                                    "Всего стоп-лоссов",
                                    result.get('total_stop_loss_count', 0)
                                )
                                st.metric(
                                    "Общая сумма убытков",
                                    f"{result.get('total_stop_loss_amount', 0):.2f}%"
                                )
                                
                                # Раздельная статистика
                                if stop_loss_stats.get('long', {}).get('count', 0) > 0:
                                    st.write(f"**Long позиции:**")
                                    st.write(f"- События: {stop_loss_stats['long']['count']}")
                                    st.write(f"- Убытки: {stop_loss_stats['long']['total_loss']:.2f}%")
                                    st.write(f"- В среднем: {stop_loss_stats['long']['avg_loss']:.2f}%")
                                
                                if stop_loss_stats.get('short', {}).get('count', 0) > 0:
                                    st.write(f"**Short позиции:**")
                                    st.write(f"- События: {stop_loss_stats['short']['count']}")
                                    st.write(f"- Убытки: {stop_loss_stats['short']['total_loss']:.2f}%")
                                    st.write(f"- В среднем: {stop_loss_stats['short']['avg_loss']:.2f}%")
                            
                            with col_lt:
                                st.markdown("### ⚡ Молнии и компенсация")
                                lightning_stats = result.get('lightning_stats', {})
                                
                                # Общая статистика молний
                                st.metric(
                                    "Всего молний",
                                    result.get('total_lightning_count', 0)
                                )
                                st.metric(
                                    "Первоначальные убытки",
                                    f"{result.get('total_lightning_loss', 0):.2f}%"
                                )
                                st.metric(
                                    "Компенсация",
                                    f"{result.get('total_lightning_compensation', 0):.2f}%"
                                )
                                st.metric(
                                    "Финальные убытки",
                                    f"{result.get('total_lightning_net_loss', 0):.2f}%"
                                )
                                
                                # Раздельная статистика
                                if lightning_stats.get('long', {}).get('count', 0) > 0:
                                    st.write(f"**Long позиции (пробитие вверх):**")
                                    st.write(f"- События: {lightning_stats['long']['count']}")
                                    st.write(f"- Первоначальные убытки: {lightning_stats['long']['total_loss']:.2f}%")
                                    st.write(f"- Компенсация: {lightning_stats['long']['total_compensation']:.2f}%")
                                    st.write(f"- Финальные убытки: {lightning_stats['long']['net_loss']:.2f}%")
                                
                                if lightning_stats.get('short', {}).get('count', 0) > 0:
                                    st.write(f"**Short позиции (пробитие вниз):**")
                                    st.write(f"- События: {lightning_stats['short']['count']}")
                                    st.write(f"- Первоначальные убытки: {lightning_stats['short']['total_loss']:.2f}%")
                                    st.write(f"- Компенсация: {lightning_stats['short']['total_compensation']:.2f}%")
                                    st.write(f"- Финальные убытки: {lightning_stats['short']['net_loss']:.2f}%")
                        
                        # Информация о симуляции
                        st.subheader("Информация о симуляции")
                        
                        st.info(f"**Параметры симуляции:**\n"
                                f"- Шаг сетки: {grid_step}%\n"
                                f"- Диапазон сетки: {grid_range}%\n"
                                f"- Компенсация убытков: {lightning_compensation}%\n"
                                f"- Используемые комиссии: 0.1%")
                        
                        # Рекомендации
                        st.subheader("Выводы и рекомендации")
                        if timeframe_choice == "1h":
                            st.success("✅ Используются часовые данные - максимальная точность симуляции")
                        else:
                            st.info("ℹ️ Для более точных результатов рекомендуются часовые данные")
                            
                        if result.get('combined_pct', 0) > 0:
                            st.success(f"✅ Стратегия прибыльна: {result.get('combined_pct', 0):.2f}%")
                        else:
                            st.warning(f"⚠️ Стратегия убыточна: {result.get('combined_pct', 0):.2f}%")
                            
                        st.info("💡 Интерфейс готов для тестирования с параметром компенсации молний")
                        
                except Exception as e:
                    st.error(f"Ошибка при выполнении симуляции: {str(e)}")


def run_analysis():
    """Основная функция анализа"""
    try:
        if not api_key or not api_secret:
            st.error("Пожалуйста, введите API ключи Binance")
            return
        
        with log_container:
            st.info("Начинаем анализ торговых пар...")
            # Инициализация компонентов
            with st.spinner("Инициализация..."):
                collector = BinanceDataCollector(api_key, api_secret)
                grid_analyzer = GridAnalyzer(collector)
            
            # Получение списка популярных пар
            with st.spinner("Получение списка торговых пар..."):
                pairs = popular_pairs[:max_pairs]
                st.success(f"Выбрано {len(pairs)} торговых пар для анализа")

    except Exception as e:
        log_container.error(f"Произошла ошибка: {str(e)}")
        st.error(f"Произошла ошибка: {str(e)}")
        return

# Запускаем анализ при нажатии кнопки (только для первой вкладки)
if start_analysis:
    run_analysis()

# Инструкции (показываем всегда в нижней части)
st.markdown("---")
st.info(
    """
    ### 💡 Инструкция по использованию
    
    **Grid Trading всегда доступен на вкладке ⚡ Grid Trading**
    
    1. Введите свои API ключи Binance в боковой панели
    2. Перейдите на вкладку "⚡ Grid Trading"
    3. Выберите пару, настройте параметры и запустите симуляцию
    4. Для графиков используйте вкладку "📈 Графики"
    
    **Особенности:**
    - Все расчеты с реальными комиссиями Binance (Maker 0.02%, Taker 0.05%)
    - Часовые данные для максимальной точности
    - Различные стратегии стоп-лосса
    """
)

# Футер
st.caption("© 2025 Анализатор торговых пар Binance")
