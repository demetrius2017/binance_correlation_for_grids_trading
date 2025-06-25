"""
Тестовый скрипт для проверки модуля оптимизации
"""

import sys
import os
import pandas as pd
import numpy as np

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.optimizer import GridOptimizer, OptimizationParams

def create_test_data(days=100):
    """Создает тестовые данные для проверки"""
    dates = pd.date_range(start='2024-01-01', periods=days*24, freq='H')
    
    # Генерируем цены с трендом и волатильностью
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.02, len(dates))  # Небольшой положительный тренд
    
    prices = [100.0]  # Начальная цена
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices[:-1],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'close': prices[1:],
        'volume': np.random.uniform(1000000, 5000000, len(dates))
    })
    
    df.set_index('timestamp', inplace=True)
    return df

class MockGridAnalyzer:
    """Мок-объект для тестирования без реального API"""
    
    def __init__(self):
        pass
    
    def estimate_dual_grid_by_candles_realistic(self, df, initial_balance_long, initial_balance_short,
                                               grid_range_pct, grid_step_pct, order_size_usd_long,
                                               order_size_usd_short, commission_pct, stop_loss_pct=None,
                                               debug=False):
        """
        Упрощенная симуляция для тестирования
        Возвращает случайные результаты на основе параметров
        """
        
        # Простая эвристика: меньший шаг = больше сделок, но меньше прибыли за сделку
        trades_multiplier = max(1, int(10 / grid_step_pct))
        trades_count = min(int(len(df) * trades_multiplier * 0.1), len(df))
        
        # Базовая прибыльность зависит от диапазона сетки
        base_profit_pct = grid_range_pct * 0.1 * (len(df) / 1000)
        
        # Добавляем случайность
        np.random.seed(int(grid_range_pct * 100 + grid_step_pct * 1000))
        random_factor = np.random.uniform(0.5, 1.5)
        
        profit_pct = base_profit_pct * random_factor
        
        # Стоп-лосс может снизить прибыльность
        if stop_loss_pct and stop_loss_pct > 0:
            if np.random.random() < 0.3:  # 30% шанс срабатывания стоп-лосса
                profit_pct = -stop_loss_pct * 0.8
        
        total_pnl = initial_balance_long * (profit_pct / 100)
        commission = trades_count * 10  # Примерная комиссия
        
        stats_long = {
            'total_pnl': total_pnl,
            'total_pnl_pct': profit_pct,
            'trades_count': trades_count,
            'total_commission': commission,
            'final_balance': initial_balance_long + total_pnl
        }
        
        stats_short = {
            'total_pnl': total_pnl * 0.8,  # Short чуть хуже
            'total_pnl_pct': profit_pct * 0.8,
            'trades_count': int(trades_count * 0.8),
            'total_commission': commission * 0.8,
            'final_balance': initial_balance_short + total_pnl * 0.8
        }
        
        return stats_long, stats_short, [], []

def test_optimization():
    """Тестирует модуль оптимизации"""
    print("🧪 Тестирование модуля оптимизации...")
    
    # Создаем тестовые данные
    print("📊 Создание тестовых данных...")
    df = create_test_data(90)
    print(f"Создано {len(df)} точек данных от {df.index[0]} до {df.index[-1]}")
    
    # Создаем мок-анализатор и оптимизатор
    mock_analyzer = MockGridAnalyzer()
    optimizer = GridOptimizer(mock_analyzer)
    
    print("\n🔍 Тестирование адаптивного поиска...")
    
    def progress_callback(message):
        print(f"  ⏳ {message}")
    
    # Тестируем адаптивный поиск (быстрее для тестирования)
    results = optimizer.grid_search_adaptive(
        df=df,
        initial_balance=1000.0,
        forward_test_pct=0.3,
        iterations=2,
        points_per_iteration=10,
        progress_callback=progress_callback
    )
    
    print(f"\n✅ Получено {len(results)} результатов")
    
    if results:
        print("\n🏆 Топ-3 результата:")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. Скор: {result.combined_score:.2f}%, "
                  f"Range: {result.params.grid_range_pct:.1f}%, "
                  f"Step: {result.params.grid_step_pct:.2f}%, "
                  f"Stop: {result.params.stop_loss_pct:.1f}%")
        
        best = results[0]
        print(f"\n🥇 Лучший результат:")
        print(f"   Бэктест: {best.backtest_score:.2f}%")
        print(f"   Форвард: {best.forward_score:.2f}%")
        print(f"   Комбинированный: {best.combined_score:.2f}%")
        print(f"   Параметры: Range={best.params.grid_range_pct:.1f}%, Step={best.params.grid_step_pct:.2f}%, Stop={best.params.stop_loss_pct:.1f}%")
    
    print("\n🧬 Тестирование генетического алгоритма...")
    
    # Тестируем генетический алгоритм (упрощенная версия)
    results_genetic = optimizer.optimize_genetic(
        df=df,
        initial_balance=1000.0,
        population_size=10,
        generations=3,
        forward_test_pct=0.3,
        max_workers=2,
        progress_callback=progress_callback
    )
    
    print(f"\n✅ Генетический алгоритм дал {len(results_genetic)} результатов")
    
    if results_genetic:
        best_genetic = results_genetic[0]
        print(f"🥇 Лучший результат от ГА:")
        print(f"   Комбинированный скор: {best_genetic.combined_score:.2f}%")
        print(f"   Параметры: Range={best_genetic.params.grid_range_pct:.1f}%, Step={best_genetic.params.grid_step_pct:.2f}%, Stop={best_genetic.params.stop_loss_pct:.1f}%")
    
    print("\n🎉 Тестирование завершено успешно!")

if __name__ == "__main__":
    test_optimization()
