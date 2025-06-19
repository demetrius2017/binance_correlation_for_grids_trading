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
    st.header("Настройки")
    
    # Загрузка сохраненных API ключей
    saved_api_key, saved_api_secret = load_api_keys()
    
    # Ввод API ключей
    api_key = st.text_input("API Key", value=saved_api_key)
    api_secret = st.text_input("API Secret", value=saved_api_secret, type="password")
    
    # Кнопка сохранения API ключей
    if st.button("Сохранить API ключи"):
        if api_key and api_secret:
            save_api_keys(api_key, api_secret)
            st.success("API ключи успешно сохранены!")
        else:
            st.error("Введите API ключи для сохранения.")
    
    st.subheader("Параметры анализа")
    
    # Параметры анализа
    min_age_days = st.slider("Минимальный возраст пары (дней)", 30, 365, 365)
    min_volatility = st.slider("Минимальная дневная волатильность (%)", 1.0, 10.0, 5.0, 0.5)
    max_range_percent = st.slider("Максимальный диапазон боковика (%)", 10.0, 50.0, 30.0, 1.0)
    
    # Параметры ранжирования
    st.subheader("Параметры ранжирования")
    volatility_weight = st.slider("Вес волатильности", 0.0, 1.0, 0.7, 0.1)
    sideways_weight = st.slider("Вес боковика", 0.0, 1.0, 0.3, 0.1)
    
    # Параметры корреляции
    st.subheader("Параметры корреляции")
    correlation_method = st.selectbox("Метод расчета корреляции", ["pearson", "spearman", "kendall"])
    correlation_threshold = st.slider("Пороговое значение корреляции", 0.1, 0.9, 0.3, 0.1)
    
    # Параметры портфеля
    st.subheader("Параметры портфеля")
    optimization_goal = st.selectbox("Цель оптимизации", ["sharpe", "min_volatility"])
    risk_free_rate = st.slider("Безрисковая ставка (%)", 0.0, 5.0, 0.0, 0.1) / 100.0
    
    # Кнопка запуска анализа
    start_analysis = st.button("Запустить анализ", type="primary")

# Основная область для отображения результатов
tab1, tab2, tab3, tab4 = st.tabs(["Рейтинг пар", "Корреляции", "Оптимальный портфель", "Графики"])

# Функция для выполнения анализа
def run_analysis():
    if not api_key or not api_secret:
        st.error("Пожалуйста, введите API ключи Binance")
        return
    
    # Отображаем прогресс
    progress_text = "Анализ торговых пар. Пожалуйста, подождите..."
    progress_bar = st.progress(0, text=progress_text)
    
    # Создаем контейнер для логов
    log_container = st.empty()
    log_container.info("Инициализация процесса анализа...")
    
    try:
        # Инициализация классов
        collector = BinanceDataCollector(api_key, api_secret)
        processor = DataProcessor(collector)
        correlation_analyzer = CorrelationAnalyzer(collector)
        portfolio_builder = PortfolioBuilder(collector, correlation_analyzer)
        
        # Тестовый запрос для проверки подключения к API
        log_container.info("Проверка подключения к Binance API...")
        status = collector.client.get_system_status()
        log_container.success(f"Подключение к Binance API успешно установлено! Статус: {status['msg']}")
        
        # Сохраняем API ключи, если они успешно работают и еще не сохранены
        saved_api_key, saved_api_secret = load_api_keys()
        if (not saved_api_key or not saved_api_secret) and api_key and api_secret:
            save_api_keys(api_key, api_secret)
            log_container.success("API ключи автоматически сохранены для будущего использования")
        
        # Шаг 1: Получение и анализ пар
        progress_bar.progress(10, text="Получение списка пар...")
        log_container.info("Получение списка всех торговых пар с Binance...")
        all_pairs = collector.get_all_usdt_pairs()
        log_container.info(f"Найдено {len(all_pairs)} торговых пар с USDT")
        
        progress_bar.progress(20, text="Фильтрация пар по возрасту...")
        log_container.info("Фильтрация пар по возрасту (не менее 1 года)...")
        
        # Анализируем пары
        log_container.info("Анализ торговых пар...")
        analyzed = processor.analyze_all_pairs(
            min_age_days=min_age_days,
            min_volatility=min_volatility,
            max_range_percent=max_range_percent
        )
        
        if analyzed.empty:
            log_container.warning("Не найдено подходящих пар.")
            st.warning("Не найдено подходящих пар. Попробуйте изменить параметры.")
            return
        
        log_container.success(f"Найдено {len(analyzed)} подходящих пар!")
        
        progress_bar.progress(40, text="Ранжирование пар...")
        log_container.info("Ранжирование пар по заданным критериям...")
        
        # Ранжируем пары
        ranked = processor.rank_pairs(
            volatility_weight=volatility_weight,
            sideways_weight=sideways_weight
        )
        
        # Выбираем топ-10 пар для дальнейшего анализа
        top_pairs = processor.get_top_pairs(10)
        symbols = top_pairs['symbol'].tolist()
        
        log_container.success(f"Топ пары: {', '.join(symbols)}")
        
        progress_bar.progress(60, text="Расчет корреляций...")
        log_container.info("Сбор данных о ценах для корреляционного анализа...")
          # Собираем данные о ценах для корреляционного анализа
        price_data = correlation_analyzer.collect_price_data(symbols, days=min_age_days)
        
        log_container.info("Расчет матрицы корреляций...")
        # Рассчитываем матрицу корреляций
        correlation = correlation_analyzer.calculate_correlation(method=correlation_method)
        
        log_container.info("Поиск наименее коррелированных пар...")
        # Находим наименее коррелированные пары
        least_correlated = correlation_analyzer.find_least_correlated_pairs(
            threshold=correlation_threshold,
            min_pairs=5
        )
        
        if len(least_correlated) < 2:
            log_container.warning(f"Найдено недостаточно некоррелированных пар: {len(least_correlated)}. Необходимо минимум 2.")
            log_container.info("Используем топ пары для формирования портфеля...")
            # Если найдено меньше 2 пар, используем топовые пары для портфеля
            least_correlated = symbols[:min(5, len(symbols))]
        
        log_container.success(f"Наименее коррелированные пары: {', '.join(least_correlated)}")
        
        progress_bar.progress(80, text="Формирование оптимального портфеля...")
        log_container.info("Формирование оптимального портфеля...")
        
        # Устанавливаем символы для портфеля
        portfolio_builder.set_portfolio_symbols(least_correlated)
        
        # Строим оптимальный портфель
        portfolio_stats = portfolio_builder.build_optimal_portfolio(
            optimization_goal=optimization_goal,
            risk_free_rate=risk_free_rate
        )
        
        progress_bar.progress(100, text="Анализ завершен!")
        log_container.success("Анализ успешно завершен!")
        time.sleep(1)
        progress_bar.empty()
        log_container.empty()
        
        # Отображаем результаты
        with tab1:
            st.header("Рейтинг торговых пар")
            st.dataframe(
                ranked[['symbol', 'avg_daily_volatility', 'price_range_percent', 'is_sideways', 'total_score']]
                .rename(columns={
                    'symbol': 'Символ',
                    'avg_daily_volatility': 'Средняя волатильность (%)',
                    'price_range_percent': 'Диапазон цены (%)',
                    'is_sideways': 'В боковике',
                    'total_score': 'Итоговый рейтинг'
                })
                .style.format({
                    'Средняя волатильность (%)': '{:.2f}',
                    'Диапазон цены (%)': '{:.2f}',
                    'Итоговый рейтинг': '{:.4f}'
                })
                .background_gradient(subset=['Итоговый рейтинг'], cmap='viridis')
            )
            
        with tab2:
            st.header("Корреляционная матрица")
            st.write("Метод расчета корреляции:", correlation_method)
            
            # Отображаем матрицу корреляций
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(correlation, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5, ax=ax)
            ax.set_title(f"Матрица корреляций ({correlation_method})")
            st.pyplot(fig)
            
            st.subheader("Наименее коррелированные пары")
            st.write(", ".join(least_correlated))
            
        with tab3:
            st.header("Оптимальный портфель")
            st.write("Цель оптимизации:", optimization_goal)
            
            # Отображаем статистику портфеля
            if portfolio_stats:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Веса в портфеле")
                    weights_df = pd.DataFrame({
                        'Символ': portfolio_stats['symbols'],
                        'Вес (%)': [w * 100 for w in portfolio_stats['weights']]
                    })
                    st.dataframe(weights_df.style.format({'Вес (%)': '{:.2f}'}))
                
                with col2:
                    st.subheader("Статистика портфеля")
                    stats_df = pd.DataFrame({
                        'Метрика': ['Ожидаемая доходность', 'Волатильность', 'Коэффициент Шарпа'],
                        'Значение': [
                            portfolio_stats['expected_return'],
                            portfolio_stats['volatility'],
                            portfolio_stats['sharpe_ratio']
                        ]
                    })
                    st.dataframe(stats_df.style.format({'Значение': '{:.4f}'}))
                  # Отображаем график весов портфеля
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.bar(portfolio_stats['symbols'], [w * 100 for w in portfolio_stats['weights']])
                ax.set_title("Распределение весов в оптимальном портфеле")
                ax.set_ylabel("Вес (%)")
                ax.set_xlabel("Символ")
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.warning("Не удалось построить оптимальный портфель.")
                
        with tab4:
            st.header("Графики цен")
            
            # Выбор пары для отображения
            selected_symbol = st.selectbox("Выберите пару для отображения", symbols)
            
            if selected_symbol:
                try:
                    # Получаем данные для выбранной пары
                    pair_data = collector.get_historical_data(
                        selected_symbol, Client.KLINE_INTERVAL_1DAY, days=min_age_days
                    )
                    
                    if not pair_data.empty:
                        # Строим график цены
                        fig, ax = plt.subplots(figsize=(12, 6))
                        ax.plot(pair_data.index, pair_data['close'])
                        ax.set_title(f"Цена {selected_symbol}")
                        ax.set_ylabel("Цена")
                        ax.set_xlabel("Дата")
                        ax.grid(True)
                        st.pyplot(fig)
                        
                        # Отображаем статистику по паре
                        stats = next((item for item in ranked.to_dict('records') 
                                    if item['symbol'] == selected_symbol), None)
                        
                        if stats:
                            st.subheader("Статистика по паре")
                            st.write(f"Средняя дневная волатильность: {stats['avg_daily_volatility']:.2f}%")
                            st.write(f"Диапазон цены: {stats['price_range_percent']:.2f}%")
                            st.write(f"В боковике: {'Да' if stats['is_sideways'] else 'Нет'}")
                            st.write(f"Итоговый рейтинг: {stats['total_score']:.4f}")
                    else:
                        st.warning("Данные для выбранной пары недоступны.")
                except Exception as e:
                    st.error(f"Ошибка при получении данных: {str(e)}")
    
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
        """
    )


# Футер
st.markdown("---")
st.caption("© 2025 Анализатор торговых пар Binance")
