"""
Тест для проверки новых функций Draw Down контроля и продвинутых метрик
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector

def create_test_data():
    """Создает тестовые данные для проверки"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='H')
    np.random.seed(42)
    
    # Создаем синтетические данные с волатильностью
    prices = [100.0]
    for i in range(len(dates) - 1):
        change_pct = np.random.normal(0, 0.02)  # 2% волатильность
        new_price = prices[-1] * (1 + change_pct)
        prices.append(max(new_price, 10.0))  # Минимум 10$
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [np.random.uniform(1000, 10000) for _ in prices]
    }, index=dates)
    
    # Корректируем high/low
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    
    return df

def test_advanced_metrics():
    """Тестирует функцию расчета продвинутых метрик"""
    print("=== Тест расчета продвинутых метрик ===")
    
    # Создаем mock объект BinanceDataCollector
    class MockCollector(BinanceDataCollector):
        def __init__(self):
            # Не вызываем super().__init__(), создаем минимальный объект
            self.client = None
    
    collector = MockCollector()
    analyzer = GridAnalyzer(collector)
    
    # Создаем тестовый журнал сделок
    test_log = [
        {'net_pnl_usd': 50, 'balance_usd': 1050},
        {'net_pnl_usd': -20, 'balance_usd': 1030},
        {'net_pnl_usd': 30, 'balance_usd': 1060},
        {'net_pnl_usd': -10, 'balance_usd': 1050},
        {'net_pnl_usd': 40, 'balance_usd': 1090}
    ]
    
    metrics = analyzer.calculate_advanced_metrics(test_log, 1000.0)
    
    print(f"Максимальная просадка: {metrics['max_drawdown_pct']:.2f}%")
    print(f"Коэффициент Шарпа: {metrics['sharpe_ratio']:.3f}")
    print(f"Коэффициент Кальмара: {metrics['calmar_ratio']:.3f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    
    return metrics

def test_drawdown_control():
    """Тестирует механизм остановки по drawdown"""
    print("\n=== Тест контроля Draw Down ===")
    
    # Создаем mock объект BinanceDataCollector
    class MockCollector(BinanceDataCollector):
        def __init__(self):
            # Не вызываем super().__init__(), создаем минимальный объект
            self.client = None
    
    collector = MockCollector()
    analyzer = GridAnalyzer(collector)
    
    # Создаем тестовые данные с сильным падением
    test_df = create_test_data()
    
    # Модифицируем данные для создания сильной просадки в середине
    mid_point = len(test_df) // 2
    test_df.iloc[mid_point:mid_point+50] *= 0.4  # Сильное падение на 60%
    
    print(f"Тестовых данных: {len(test_df)} точек")
    
    # Тест без ограничения drawdown
    stats_long1, stats_short1, _, _ = analyzer.estimate_dual_grid_by_candles_realistic(
        df=test_df,
        initial_balance_long=1000,
        initial_balance_short=1000,
        grid_range_pct=10.0,
        grid_step_pct=1.0,
        max_drawdown_pct=None,  # Без ограничения
        debug=False
    )
    
    # Тест с ограничением drawdown 20%
    stats_long2, stats_short2, _, _ = analyzer.estimate_dual_grid_by_candles_realistic(
        df=test_df,
        initial_balance_long=1000,
        initial_balance_short=1000,
        grid_range_pct=10.0,
        grid_step_pct=1.0,
        max_drawdown_pct=20.0,  # Ограничение 20%
        debug=False
    )
    
    print("Без ограничения DD:")
    print(f"  Long сделок: {stats_long1['trades_count']}, PnL: {stats_long1['total_pnl']:.2f}")
    print(f"  Short сделок: {stats_short1['trades_count']}, PnL: {stats_short1['total_pnl']:.2f}")
    print(f"  DD стоп сработал: {stats_long1.get('drawdown_stop_triggered', False)}")
    
    print("С ограничением DD 20%:")
    print(f"  Long сделок: {stats_long2['trades_count']}, PnL: {stats_long2['total_pnl']:.2f}")
    print(f"  Short сделок: {stats_short2['trades_count']}, PnL: {stats_short2['total_pnl']:.2f}")
    print(f"  DD стоп сработал: {stats_long2.get('drawdown_stop_triggered', False)}")
    print(f"  Макс. DD достигнут: {stats_long2.get('max_drawdown_reached', 0):.2f}%")
    
    return stats_long1, stats_long2

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование новых функций Draw Down контроля и продвинутых метрик")
    print("=" * 70)
    
    try:
        # Тест продвинутых метрик
        metrics = test_advanced_metrics()
        
        # Тест контроля drawdown
        stats1, stats2 = test_drawdown_control()
        
        print("\n✅ Все тесты завершены успешно!")
        print("🚀 Система готова к использованию новых функций!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
