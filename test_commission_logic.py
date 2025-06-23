"""
Тест симуляции двойных сеток с реальными комиссиями Binance.
Только реальные комиссии, тесты прибыльности на часовых данных.
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.collector import BinanceDataCollector
from modules.grid_analyzer import GridAnalyzer, MAKER_COMMISSION_RATE, TAKER_COMMISSION_RATE

def test_hourly_profitability():
    """Тестирование прибыльности на часовых данных с реальными комиссиями"""
    
    print("=== ТЕСТ ПРИБЫЛЬНОСТИ НА ЧАСОВЫХ ДАННЫХ ===")
    print(f"Реальные комиссии Binance:")
    print(f"  Maker: {MAKER_COMMISSION_RATE*100:.3f}%")
    print(f"  Taker: {TAKER_COMMISSION_RATE*100:.3f}%")
    print()
    
    # Загрузка конфигурации
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            api_key = config.get("api_key", "")
            api_secret = config.get("api_secret", "")
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        return
    
    # Инициализация
    collector = BinanceDataCollector(api_key, api_secret)
    grid_analyzer = GridAnalyzer(collector)
    
    # Получаем тестовые пары (можно оставить на дневных для выбора)
    print("Получаем список доступных пар...")
    old_pairs = collector.get_pairs_older_than_year()
    
    if not old_pairs:
        print("Нет доступных пар для тестирования")
        return
    
    # Тестируем прибыльность на первых 3 парах с часовыми данными
    test_pairs = old_pairs[:3]
    print(f"Тестируем прибыльность на парах: {test_pairs}")
    print("Используем часовые данные для точного анализа прибыльности")
    print()
    
    profitability_results = []
    
    for symbol in test_pairs:
        print(f"--- Анализ прибыльности {symbol} (часовые данные) ---")
        
        # Получаем часовые данные за 30 дней для точного анализа
        df_hourly = collector.get_historical_data(symbol, "1h", 30*24)
        
        if df_hourly.empty:
            print(f"Нет часовых данных для {symbol}")
            continue
        
        print(f"Загружено {len(df_hourly)} часовых свечей")
        
        # Тестируем оптимальные параметры с реальными комиссиями
        result = grid_analyzer.estimate_dual_grid_by_candles(
            df_hourly, 
            grid_range_pct=10.0,
            grid_step_pct=0.5,  # Оптимальный шаг для часовых данных
            use_real_commissions=True,
            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            stop_loss_strategy="independent"
        )
        
        print(f"Результаты для {symbol}:")
        print(f"  Общая доходность: {result['combined_pct']:.2f}%")
        print(f"  Long: {result['long_pct']:.2f}%, Short: {result['short_pct']:.2f}%")
        print(f"  Всего сделок: {result['total_trades']}")
        print(f"  Maker: {result['long_maker_trades'] + result['short_maker_trades']}, Taker: {result['long_taker_trades'] + result['short_taker_trades']}")
        print(f"  Молний: {result['lightning_count']}, Стоп-лоссов: {result['stop_loss_count']}")
        print(f"  Эффективный шаг: {result['grid_step_pct']:.2f}%")
        
        # Сохраняем результаты
        profitability_results.append({
            'symbol': symbol,
            'combined_pnl': result['combined_pct'],
            'long_pnl': result['long_pct'],
            'short_pnl': result['short_pct'],
            'total_trades': result['total_trades'],
            'maker_trades': result['long_maker_trades'] + result['short_maker_trades'],
            'taker_trades': result['long_taker_trades'] + result['short_taker_trades'],
            'lightning_count': result['lightning_count'],
            'stop_loss_count': result['stop_loss_count'],
            'grid_step': result['grid_step_pct']
        })
        
        print("-" * 50)
    
    # Итоговый анализ прибыльности
    if profitability_results:
        print("\n=== ИТОГОВЫЙ АНАЛИЗ ПРИБЫЛЬНОСТИ ===")
        df_results = pd.DataFrame(profitability_results)
        
        print(f"Протестировано пар: {len(df_results)}")
        print(f"Средняя доходность: {df_results['combined_pnl'].mean():.2f}%")
        print(f"Медианная доходность: {df_results['combined_pnl'].median():.2f}%")
        print(f"Лучший результат: {df_results['combined_pnl'].max():.2f}%")
        print(f"Худший результат: {df_results['combined_pnl'].min():.2f}%")
        
        print(f"\nСреднее количество сделок: {df_results['total_trades'].mean():.0f}")
        print(f"Среднее соотношение Maker/Taker: {df_results['maker_trades'].sum()}/{df_results['taker_trades'].sum()}")
        
        # Лучшие и худшие пары
        best_pair = df_results.loc[df_results['combined_pnl'].idxmax()]
        worst_pair = df_results.loc[df_results['combined_pnl'].idxmin()]
        
        print(f"\nЛучшая пара: {best_pair['symbol']} ({best_pair['combined_pnl']:.2f}%)")
        print(f"Худшая пара: {worst_pair['symbol']} ({worst_pair['combined_pnl']:.2f}%)")
        
        # Рентабельность
        profitable_pairs = len(df_results[df_results['combined_pnl'] > 0])
        print(f"\nПрибыльных пар: {profitable_pairs}/{len(df_results)} ({profitable_pairs/len(df_results)*100:.1f}%)")
        
        # Сохраняем результаты
        df_results.to_csv('hourly_profitability_results.csv', index=False)
        print(f"\nРезультаты сохранены в hourly_profitability_results.csv")

def test_specific_scenarios():
    """Тестирование специфических сценариев"""
    
    print("\n=== ТЕСТ СПЕЦИФИЧЕСКИХ СЦЕНАРИЕВ ===")
    
    # Загрузка конфигурации
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            api_key = config.get("api_key", "")
            api_secret = config.get("api_secret", "")
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        return
    
    collector = BinanceDataCollector(api_key, api_secret)
    grid_analyzer = GridAnalyzer(collector)
    
    # Тестируем ICXUSDT (из предыдущих тестов)
    symbol = "ICXUSDT"
    print(f"Тестируем {symbol} с разными параметрами...")
    
    df = collector.get_historical_data(symbol, "1d", 30)
    if df.empty:
        print(f"Нет данных для {symbol}")
        return
    
    # Тестируем разные шаги сетки
    grid_steps = [0.3, 0.5, 0.8, 1.0]
    
    for step in grid_steps:
        print(f"\n--- Шаг сетки: {step}% ---")
        
        result = grid_analyzer.estimate_dual_grid_by_candles(
            df,
            grid_range_pct=20.0,
            grid_step_pct=step,
            use_real_commissions=True,
            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            stop_loss_strategy="independent"
        )
        
        print(f"Доходность: {result['combined_pct']:.2f}% (Long: {result['long_pct']:.2f}%, Short: {result['short_pct']:.2f}%)")
        print(f"Сделок: {result['total_trades']} (Maker: {result['long_maker_trades'] + result['short_maker_trades']}, "
              f"Taker: {result['long_taker_trades'] + result['short_taker_trades']})")
        print(f"Эффективный шаг: {result['grid_step_pct']:.2f}%")
    
    # Тестируем разные стратегии стоп-лосса
    print(f"\n--- Тест стратегий стоп-лосса ---")
    
    strategies = ["independent", "close_both"]
    
    for strategy in strategies:
        print(f"\nСтратегия: {strategy}")
        
        result = grid_analyzer.estimate_dual_grid_by_candles(
            df,
            grid_range_pct=20.0,
            grid_step_pct=0.5,
            use_real_commissions=True,
            stop_loss_pct=3.0,  # Более агрессивный стоп-лосс
            stop_loss_coverage=0.7,
            stop_loss_strategy=strategy,
            close_both_on_stop_loss=(strategy == "close_both")
        )
        
        print(f"Доходность: {result['combined_pct']:.2f}%")
        print(f"Long активна: {result['long_active']}, Short активна: {result['short_active']}")
        print(f"Стоп-лоссов: {result['stop_loss_count']}")

if __name__ == "__main__":
    test_hourly_profitability()
    test_specific_scenarios()
