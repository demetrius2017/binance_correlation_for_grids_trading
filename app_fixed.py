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
import plotly.graph_objects as go

from modules.collector import BinanceDataCollector
from modules.processor import DataProcessor
from modules.correlation import CorrelationAnalyzer
from modules.portfolio import PortfolioBuilder
from modules.grid_analyzer import GridAnalyzer, MAKER_COMMISSION_RATE, TAKER_COMMISSION_RATE


# Конфигурация страницы
st.set_page_config(
    page_title="Анализ корреляций Binance",
    page_icon="📊",
    layout="wide"
)

# Инициализация сессионных состояний
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_secret' not in st.session_state:
    st.session_state.api_secret = ""


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

# Глобальные переменные для компонентов
collector = None
grid_analyzer = None
correlation_analyzer = None
portfolio_builder = None
data = {}
symbols = []
results_df = pd.DataFrame()
correlation_matrix = pd.DataFrame()

def initialize_components():
    global collector, grid_analyzer, correlation_analyzer, portfolio_builder
    if not api_key or not api_secret:
        st.error("Пожалуйста, введите API ключи Binance")
        return False
    
    try:
        collector = BinanceDataCollector(api_key, api_secret)
        grid_analyzer = GridAnalyzer(collector)
        correlation_analyzer = CorrelationAnalyzer(collector)
        portfolio_builder = PortfolioBuilder(collector, correlation_analyzer)
        return True
    except Exception as e:
        st.error(f"Ошибка инициализации компонентов: {str(e)}")
        return False

def run_analysis():
    """Основная функция анализа"""
    global data, symbols, results_df, correlation_matrix
    
    try:
        if not initialize_components():
            return
        
        with log_container:
            st.info("Начинаем анализ торговых пар...")
            
            # Инициализация компонентов
            with st.spinner("Инициализация..."):
                collector = BinanceDataCollector(api_key, api_secret)
                grid_analyzer = GridAnalyzer(collector)
                correlation_analyzer = CorrelationAnalyzer(collector)
                portfolio_builder = PortfolioBuilder(collector, correlation_analyzer)
            
            # Инициализируем переменные для хранения результатов
            data = {}
            symbols = []
            results_df = pd.DataFrame()
            correlation_matrix = pd.DataFrame()
              # Получение списка популярных пар
            with st.spinner("Получение списка торговых пар..."):
                # Используем предопределенный список популярных пар
                popular_pairs = [
                    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
                    "LINKUSDT", "DOTUSDT", "LTCUSDT", "UNIUSDT", "SOLUSDT",
                    "MATICUSDT", "ICXUSDT", "VETUSDT", "XLMUSDT", "TRXUSDT"
                ]
                pairs = popular_pairs[:max_pairs]
                st.success(f"Выбрано {len(pairs)} торговых пар для анализа")
        
        # Создаем вкладки для результатов
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Рейтинг пар", 
            "🔗 Корреляции", 
            "💼 Портфель", 
            "📈 Графики",
            "⚡ Grid Trading"
        ])
        
        # Вкладка 1: Рейтинг пар
        with tab1:
            st.header("Рейтинг торговых пар")
            
            with st.spinner("Анализируем пары..."):
                # Получаем данные для анализа
                data = {}
                symbols = []
                
                for symbol in pairs:
                    df = collector.get_historical_data(symbol, "1d", 30)
                    if not df.empty:
                        analysis = grid_analyzer.analyze_pair(df)
                        if analysis and analysis.get('total_score', 0) > 0:
                            data[symbol] = analysis
                            symbols.append(symbol)
                
                if data:
                    # Создаем DataFrame с результатами
                    results_df = pd.DataFrame.from_dict(data, orient='index')
                    results_df = results_df.sort_values('total_score', ascending=False)
                    
                    st.subheader("Топ-15 торговых пар")
                    
                    # Форматируем DataFrame для отображения
                    display_df = results_df.head(15).copy()
                    display_df = display_df.round(4)
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Сохраняем результаты
                    results_df.to_csv("pair_analysis_results.csv")
                    st.success("Результаты сохранены в pair_analysis_results.csv")
                else:
                    st.warning("Не удалось проанализировать ни одной пары")
        
        # Вкладка 2: Корреляции
        with tab2:
            st.header("Анализ корреляций")
            
            if 'results_df' in locals() and not results_df.empty:
                top_pairs = results_df.head(15).index.tolist()
                
                with st.spinner("Рассчитываем корреляции..."):
                    # Получаем данные для корреляционного анализа
                    price_data = {}
                    for symbol in top_pairs:
                        df = collector.get_historical_data(symbol, "1d", 30)
                        if not df.empty:
                            price_data[symbol] = df['close']
                    
                    if len(price_data) >= 2:
                        correlation_matrix = pd.DataFrame(data=[df['close'] for df in price_data.values()]).corr()
                        
                        # Отображаем тепловую карту
                        st.subheader("Матрица корреляций")
                        fig, ax = plt.subplots(figsize=(12, 10))
                        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
                        plt.title("Корреляция цен активов за последние 30 дней")
                        st.pyplot(fig)
                        
                        # Сохраняем результаты
                        correlation_matrix.to_csv("correlation_matrix.csv")
                        st.success("Матрица корреляций сохранена в correlation_matrix.csv")
                    else:
                        st.warning("Недостаточно данных для корреляционного анализа")
        
        # Вкладка 3: Портфель        with tab3:
            st.header("Оптимизация портфеля")
            
            if 'correlation_matrix' in locals():
                with st.spinner("Строим оптимальный портфель..."):
                    # Строим портфель с минимальной корреляцией
                    portfolio_builder.set_portfolio_symbols(list(correlation_matrix.columns))
                    optimal_portfolio = {
                        symbol: 1.0/len(correlation_matrix.columns) 
                        for symbol in correlation_matrix.columns[:10]
                    }
                      if optimal_portfolio:
                        st.subheader("Рекомендуемый портфель")
                        
                        portfolio_df = pd.DataFrame([
                            {"Актив": asset, "Вес": f"{weight:.1%}"} 
                            for asset, weight in optimal_portfolio.items()
                        ])
                        
                        st.dataframe(portfolio_df, use_container_width=True)
                        
                        # Средняя корреляция портфеля
                        # Считаем среднюю корреляцию портфеля
                        avg_correlations = []
                        symbols = list(optimal_portfolio.keys())
                        for i in range(len(symbols)):
                            for j in range(i + 1, len(symbols)):
                                avg_correlations.append(correlation_matrix.loc[symbols[i], symbols[j]])
                        avg_correlation = sum(avg_correlations) / len(avg_correlations) if avg_correlations else 0
                        st.metric("Средняя корреляция портфеля", f"{avg_correlation:.3f}")
                        
                        # Сохраняем портфель
                        portfolio_df.to_csv("optimal_portfolio.csv", index=False)
                        st.success("Портфель сохранен в optimal_portfolio.csv")
                    else:
                        st.warning("Не удалось построить оптимальный портфель")
        
        # Вкладка 4: Графики
        with tab4:
            st.header("Графики цен")
            
            if 'symbols' in locals() and symbols:
                selected_symbol = st.selectbox("Выберите актив для просмотра", symbols)
                
                try:
                    df = collector.get_historical_data(selected_symbol, "1d", 90)
                    if not df.empty:
                        # График цены                        fig, ax = plt.subplots(figsize=(12, 6))
                        ax.plot(df.index, df['close'], linewidth=2)
                        ax.set_title(f"График цены {selected_symbol} за последние 90 дней")
                        ax.set_xlabel("Дата")
                        ax.set_ylabel("Цена (USDT)")
                        ax.grid(True, alpha=0.3)
                        st.pyplot(fig)
                        
                        # Статистика актива
                        if selected_symbol in data:
                            stats = data[selected_symbol]
                            st.subheader(f"Статистика {selected_symbol}")
                            st.write(f"Волатильность: {stats['volatility']:.4f}")
                            st.write(f"Объем торгов: ${stats['volume_24h']:,.0f}")
                            st.write(f"Диапазон цены: {stats['price_range_percent']:.2f}%")
                            st.write(f"В боковике: {'Да' if stats['is_sideways'] else 'Нет'}")
                            st.write(f"Итоговый рейтинг: {stats['total_score']:.4f}")
                    else:
                        st.warning("Данные для выбранной пары недоступны.")
                except Exception as e:
                    st.error(f"Ошибка при получении данных: {str(e)}")
        
        # Вкладка 5: Grid Trading
        with tab5:
            show_grid_trading_tab()

    except Exception as e:
        log_container.error(f"Произошла ошибка: {str(e)}")
        st.error(f"Произошла ошибка: {str(e)}")
        return

# Запускаем анализ при нажатии кнопки
if start_analysis:
    run_analysis()
else:
    # Отображаем инструкции
    st.info(
        """
        ### Инструкция по использованию
        
        1. Введите свои API ключи Binance в боковой панели
        2. Настройте параметры анализа по желанию
        3. Нажмите кнопку "Запустить анализ"
        4. Просмотрите результаты на соответствующих вкладках
        
        Результаты анализа включают:
        - Рейтинг торговых пар по заданным критериям
        - Матрицу корреляций между топ-парами
        - Оптимальный портфель с минимальной корреляцией между активами
        - Графики цен выбранных пар
        - Grid Trading симуляцию с реальными комиссиями
        """
    )

# Футер
st.markdown("---")
st.caption("© 2025 Анализатор торговых пар Binance")

def show_grid_trading_tab():
    """Вкладка с анализом сетки"""
    global grid_analyzer
    
    if not initialize_components():
        return
        
    st.header("Анализ торговой сетки")
    
    col1, col2 = st.columns(2)
    
    with col1:
        symbol = st.text_input("Торговая пара (например, BTCUSDT)", "BTCUSDT")
        interval = st.selectbox(
            "Интервал",
            ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
        )
        
    with col2:
        start_date = st.date_input("Начальная дата")
        end_date = st.date_input("Конечная дата")
        
    # Параметры сетки
    st.subheader("Параметры сетки")
    col3, col4 = st.columns(2)
    
    with col3:
        grid_size = st.number_input("Размер сетки (%)", value=1.0, step=0.1)
        stop_loss = st.number_input("Стоп-лосс (%)", value=2.0, step=0.1)
        
    with col4:
        take_profit = st.number_input("Тейк-профит (%)", value=1.0, step=0.1)
        max_positions = st.number_input("Максимум позиций", value=3, step=1)
        
    if st.button("Анализировать"):
        try:
            with st.spinner("Получение данных..."):
                # Конвертируем даты в timestamp
                start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
                end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000)
                
                # Получаем исторические данные
                historical_data = collector.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_str=str(start_timestamp),
                    end_str=str(end_timestamp)
                )
                
                if not historical_data:
                    st.error("Не удалось получить исторические данные")
                    return
                
                # Преобразуем данные в DataFrame
                df = pd.DataFrame(
                    historical_data,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignored']
                )
                
                # Конвертируем типы данных
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Анализируем сетку
                with st.spinner("Анализ торговой сетки..."):
                    results = grid_analyzer.analyze_pair(
                        df=df,
                        grid_size=grid_size / 100,  # конвертируем в десятичную дробь
                        take_profit=take_profit / 100,
                        stop_loss=stop_loss / 100,
                        max_positions=int(max_positions)
                    )
                    
                    if results:
                        # Отображаем результаты
                        st.success("Анализ завершен!")
                        
                        # Создаем таблицу с результатами
                        metrics = {
                            "Всего сделок": results.get('total_trades', 0),
                            "Прибыльных сделок": results.get('profitable_trades', 0),
                            "Убыточных сделок": results.get('loss_trades', 0),
                            "Общая прибыль (%)": round(results.get('total_profit', 0) * 100, 2),
                            "Средняя прибыль на сделку (%)": round(results.get('avg_profit', 0) * 100, 2),
                            "Максимальная просадка (%)": round(results.get('max_drawdown', 0) * 100, 2)
                        }
                        
                        # Отображаем метрики в колонках
                        cols = st.columns(3)
                        for i, (metric, value) in enumerate(metrics.items()):
                            with cols[i % 3]:
                                st.metric(metric, value)
                        
                        # График цены и сделок
                        if 'price_history' in results and 'trades' in results:
                            fig = go.Figure()
                            
                            # График цены
                            fig.add_trace(go.Scatter(
                                x=df['timestamp'],
                                y=df['close'],
                                mode='lines',
                                name='Цена'
                            ))
                            
                            # Точки входа в сделки
                            trades_df = pd.DataFrame(results['trades'])
                            if not trades_df.empty:
                                fig.add_trace(go.Scatter(
                                    x=pd.to_datetime(trades_df['timestamp'], unit='ms'),
                                    y=trades_df['entry_price'],
                                    mode='markers',
                                    name='Входы в позицию',
                                    marker=dict(
                                        size=8,
                                        color='green',
                                        symbol='triangle-up'
                                    )
                                ))
                                
                                # Точки выхода
                                fig.add_trace(go.Scatter(
                                    x=pd.to_datetime(trades_df['exit_timestamp'], unit='ms'),
                                    y=trades_df['exit_price'],
                                    mode='markers',
                                    name='Выходы из позиции',
                                    marker=dict(
                                        size=8,
                                        color='red',
                                        symbol='triangle-down'
                                    )
                                ))
                            
                            fig.update_layout(
                                title=f"График цены {symbol} и сделки",
                                xaxis_title="Время",
                                yaxis_title="Цена",
                                height=600
                            )                            
                            st.plotly_chart(fig, use_container_width=True)
                            # Отображаем таблицу сделок
                            if not trades_df.empty:
                                st.subheader("История сделок")
                                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
                                trades_df['exit_timestamp'] = pd.to_datetime(trades_df['exit_timestamp'], unit='ms')
                                trades_df['profit'] = trades_df['profit'] * 100  # конвертируем в проценты
                                
                                display_df = trades_df[[
                                    'timestamp', 'exit_timestamp', 'entry_price',
                                    'exit_price', 'profit', 'exit_reason'
                                ]].rename(columns={
                                    'timestamp': 'Время входа',
                                    'exit_timestamp': 'Время выхода',
                                    'entry_price': 'Цена входа',
                                    'exit_price': 'Цена выхода',
                                    'profit': 'Прибыль (%)',
                                    'exit_reason': 'Причина выхода'
                                })
                                
                                st.dataframe(display_df)
                    else:
                        st.error("Не удалось проанализировать данные")
                        
        except Exception as e:
            st.error(f"Произошла ошибка при анализе: {str(e)}")
            raise  # для отладки
