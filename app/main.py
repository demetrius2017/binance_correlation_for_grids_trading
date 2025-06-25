import streamlit as st
from modules.collector import BinanceDataCollector
from modules.processor import DataProcessor
from modules.correlation import CorrelationAnalyzer
from modules.portfolio import PortfolioBuilder
from app.grid_trading import grid_trading_tab
from app.analysis import analysis_tab

# Константы комиссий Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02%
TAKER_COMMISSION_RATE = 0.0005  # 0.05%

# Настройка страницы
st.set_page_config(
    page_title="Анализатор торговых пар Binance",
    page_icon="4ca",
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

# Кнопка запуска анализа
start_analysis = st.button("680 Запустить анализ", type="primary")

# Создаем контейнер для логов
log_container = st.container()

# Загружаем сохраненные ключи для использования в Grid Trading
saved_api_key, saved_api_secret = load_api_keys()

# Создаем вкладки (всегда доступны)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "4ca Список пар", 
    "517 Информация", 
    "4bc Настройки", 
    "4c8 Графики",
    "50c Grid Trading"
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
    st.write("44d Анализ торговых пар")
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
    st.header("Симуляция сеточной торговли")

    # Параметры для сеточной торговли
    st.subheader("Параметры сетки")
    
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
        initial_balance = st.number_input(
            "Начальный баланс (USDT)",
            min_value=100.0,
            max_value=100000.0,
            value=1000.0,
            step=100.0,
            help="Начальный капитал для симуляции"
        )

    st.markdown("---")
    
    # Дополнительные параметры симуляции
    st.subheader("Дополнительные параметры")
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
    selected_pair_for_grid = st.selectbox(
        "Выберите пару для симуляции",
        popular_pairs,
        key="selected_pair_for_grid"
    )

    if st.button("Запустить симуляцию для выбранной пары"):
        if not saved_api_key or not saved_api_secret:
            st.error("Пожалуйста, введите и сохраните API ключи в боковой панели.")
        elif not selected_pair_for_grid:
            st.warning("Пожалуйста, выберите пару для симуляции.")
        else:
            try:
                # Инициализация инструментов
                collector = BinanceDataCollector(saved_api_key, saved_api_secret)
                grid_analyzer = GridAnalyzer(collector)
                
                # Получение исторических данных
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

                    st.success(f"Симуляция для {selected_pair_for_grid} за {simulation_days} дней завершена!")
                    
                    # Отображение результатов
                    st.subheader("Результаты симуляции")
                    
                    # Расчет комбинированных результатов
                    total_pnl = stats_long['total_pnl'] + stats_short['total_pnl']
                    total_initial_balance = initial_balance * 2
                    total_pnl_pct = (total_pnl / total_initial_balance) * 100 if total_initial_balance > 0 else 0
                    total_trades = stats_long['trades_count'] + stats_short['trades_count']
                    total_commission = stats_long['total_commission'] + stats_short['total_commission']
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("Общий PnL", f"${total_pnl:.2f}", f"{total_pnl_pct:.2f}%")
                    with col_b:
                        st.metric("Всего сделок", total_trades)
                    with col_c:
                        st.metric("Всего комиссий", f"${total_commission:.2f}")

                    st.subheader("Детальная статистика")
                    
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
                    with st.expander("Показать логи сделок"):
                        st.subheader("Лог сделок Long")
                        if log_long_df: # Проверяем, что список не пустой
                            df_long = pd.DataFrame(log_long_df)
                            st.dataframe(df_long, use_container_width=True)
                        else:
                            st.write("Сделок по Long не было.")
                            
                        st.subheader("Лог сделок Short")
                        if log_short_df: # Проверяем, что список не пустой
                            df_short = pd.DataFrame(log_short_df)
                            st.dataframe(df_short, use_container_width=True)
                        else:
                            st.write("Сделок по Short не было.")

            except Exception as e:
                st.error(f"Произошла ошибка во время симуляции: {e}")

# Основной блок запуска анализа (если кнопка нажата)
if start_analysis:
    if not api_key or not api_secret:
        log_container.error("Введите API ключи для начала анализа.")
    else:
        try:
            # Инициализация классов
            log_container.info("Инициализация модулей...")
            collector = BinanceDataCollector(api_key, api_secret)
            processor = DataProcessor(collector)
            analyzer = CorrelationAnalyzer(collector) # Исправлено: передаем collector
            portfolio_builder = PortfolioBuilder(collector, analyzer) # Исправлено: передаем collector и analyzer
            
            # Получение и фильтрация пар
            log_container.info("Получение и фильтрация торговых пар...")
            all_pairs = collector.get_all_usdt_pairs()
            filtered_pairs = processor.filter_pairs_by_volume_and_price(
                all_pairs, 
                min_volume=min_volume, 
                min_price=min_price, 
                max_price=max_price
            )
            
            # Ограничиваем количество пар для анализа
            pairs_to_analyze = filtered_pairs[:max_pairs]
            log_container.success(f"Отобрано {len(pairs_to_analyze)} пар для анализа.")
            
            # Обновляем вкладку 1 с отфильтрованными парами
            with tab1:
                st.empty() # Очищаем предыдущий контент
                st.subheader("Отфильтрованные пары для анализа")
                pairs_df = pd.DataFrame({
                    'Символ': pairs_to_analyze,
                    'Описание': [f"Торговая пара {p}" for p in pairs_to_analyze]
                })
                st.dataframe(pairs_df, use_container_width=True)
            
            # Здесь можно добавить дальнейшую логику анализа, если требуется
            # Например, расчет корреляций и построение портфеля
            
        except Exception as e:
            log_container.error(f"Произошла ошибка: {str(e)}")
            st.exception(e) # Выводим полный traceback для отладки
