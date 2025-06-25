import streamlit as st
import pandas as pd
from modules.collector import BinanceDataCollector
from modules.grid_analyzer import GridAnalyzer
from constants import TAKER_COMMISSION_RATE

# Функции для сохранения и загрузки API ключей
import json
import os

def load_api_keys():
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
            return config.get("api_key", ""), config.get("api_secret", "")
        return "", ""
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        return "", ""

def grid_trading_tab(popular_pairs):
    saved_api_key, saved_api_secret = load_api_keys()

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
                collector = BinanceDataCollector(saved_api_key, saved_api_secret)
                grid_analyzer = GridAnalyzer(collector)
                
                timeframe_in_minutes = {'15m': 15, '1h': 60, '4h': 240, '1d': 1440}
                total_minutes = simulation_days * 24 * 60
                limit = int(total_minutes / timeframe_in_minutes[timeframe])
                
                df_for_simulation = collector.get_historical_data(selected_pair_for_grid, timeframe, limit)
                
                if df_for_simulation.empty:
                    st.error("Не удалось загрузить данные для симуляции.")
                else:
                    with st.spinner(f"Запуск симуляции для {selected_pair_for_grid}..."):
                        stats_long, stats_short, log_long_df, log_short_df = grid_analyzer.estimate_dual_grid_by_candles_realistic(
                            df=df_for_simulation,
                            initial_balance_long=initial_balance,
                            initial_balance_short=initial_balance,
                            grid_range_pct=grid_range_pct,
                            grid_step_pct=grid_step_pct,
                            order_size_usd_long=0,
                            order_size_usd_short=0,
                            commission_pct=TAKER_COMMISSION_RATE * 100,
                            stop_loss_pct=stop_loss_pct if stop_loss_pct > 0 else None,
                            debug=False
                        )

                    st.success(f"Симуляция для {selected_pair_for_grid} за {simulation_days} дней завершена!")
                    
                    st.subheader("Результаты симуляции")
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
                    results_df = pd.DataFrame(results_data)
                    results_df['Значение'] = results_df['Значение'].astype(str)
                    st.dataframe(results_df, use_container_width=True)

                    with st.expander("Показать логи сделок"):
                        st.subheader("Лог сделок Long")
                        if log_long_df:
                            df_long = pd.DataFrame(log_long_df)
                            st.dataframe(df_long, use_container_width=True)
                        else:
                            st.write("Сделок по Long не было.")
                            
                        st.subheader("Лог сделок Short")
                        if log_short_df:
                            df_short = pd.DataFrame(log_short_df)
                            st.dataframe(df_short, use_container_width=True)
                        else:
                            st.write("Сделок по Short не было.")

            except Exception as e:
                st.error(f"Произошла ошибка во время симуляции: {e}")
