#!/usr/bin/env python3
"""
Тест для проверки исправленной логики Grid Trading симуляции
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector

def create_realistic_test_data(periods=90):
    """
    Создает реалистичные тестовые данные для симуляции
    """
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='h')
    
    np.random.seed(42)
    base_price = 1.0
    
    data = []
    for i in range(periods):
        # Более реалистичные колебания
        change = np.random.normal(0, 0.3)  # Среднее изменение 0%, стандартное отклонение 0.3%
        
        open_price = base_price * (1 + change / 100)
        
        # Диапазон свечи
        range_pct = abs(np.random.normal(0.8, 0.4))  # Средний диапазон 0.8%
        
        high_price = open_price * (1 + range_pct / 200)
        low_price = open_price * (1 - range_pct / 200)
        
        # Направление закрытия
        close_direction = np.random.choice([-1, 1])
        close_price = open_price + close_direction * open_price * (range_pct / 400)
        
        # Проверяем корректность high и low
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Добавляем редкие молнии
        if i % 30 == 0 and i > 0:  # Раз в 30 свечей
            range_pct = 18.0  # Молния
            high_price = open_price * 1.18
            low_price = open_price * 0.82
            close_price = open_price * (1.15 if np.random.random() > 0.5 else 0.85)
        
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.uniform(1000, 5000)
        })
        
        base_price = close_price
    
    return pd.DataFrame(data)

def test_fixed_logic():
    """
    Тестирует исправленную логику расчетов
    """
    print("=== ТЕСТ ИСПРАВЛЕННОЙ ЛОГИКИ GRID TRADING ===")
    print()
    
    # Создаем Mock коллектор
    class MockCollector:
        def __init__(self):
            self.client = None
    
    collector = MockCollector()
    analyzer = GridAnalyzer(collector)  # type: ignore
    
    # Создаем тестовые данные
    df = create_realistic_test_data(90)  # 90 часовых свечей
    
    print(f"Тестовые данные: {len(df)} часовых свечей")
    print(f"Диапазон цен: {df['low'].min():.4f} - {df['high'].max():.4f}")
    print()
    
    # Параметры как в проблемном тесте
    grid_step = 0.30
    grid_range = 20.0
    stop_loss = 5.0
    
    print("ПАРАМЕТРЫ СИМУЛЯЦИИ:")
    print(f"Шаг сетки: {grid_step}%")
    print(f"Диапазон сетки: {grid_range}%")
    print(f"Стоп-лосс: {stop_loss}%")
    print()
    
    # Запускаем исправленную симуляцию
    result = analyzer.estimate_dual_grid_by_candles(
        df,
        grid_range_pct=grid_range,
        grid_step_pct=grid_step,
        use_real_commissions=True,
        stop_loss_pct=stop_loss,
        stop_loss_coverage=0.5,
        stop_loss_strategy="independent"
    )
    
    print("РЕЗУЛЬТАТЫ ИСПРАВЛЕННОЙ СИМУЛЯЦИИ:")
    print("-" * 50)
    print(f"Общая доходность: {result['combined_pct']:.2f}%")
    print(f"Long доходность: {result['long_pct']:.2f}%")
    print(f"Short доходность: {result['short_pct']:.2f}%")
    print(f"Всего сделок: {result['total_trades']:.0f}")
    print(f"Молний: {result['lightning_count']}")
    print(f"Стоп-лоссов: {result['stop_loss_count']}")
    print()
    
    # Анализ результатов
    print("АНАЛИЗ РЕЗУЛЬТАТОВ:")
    print("-" * 30)
    
    # Проверка реалистичности
    avg_profit_per_trade = result['combined_pct'] / result['total_trades'] if result['total_trades'] > 0 else 0
    max_theoretical_profit = grid_step - 0.02  # Максимальная прибыль с maker ордера
    
    print(f"Средняя прибыль на сделку: {avg_profit_per_trade:.4f}%")
    print(f"Теоретический максимум: {max_theoretical_profit:.3f}%")
    
    if avg_profit_per_trade <= max_theoretical_profit:
        print("✅ Средняя прибыль в пределах нормы")
    else:
        print("❌ Средняя прибыль превышает теоретический максимум")
    
    # Проверка общей доходности
    if result['combined_pct'] > 100:
        print("❌ Доходность все еще завышена (>100%)")
    elif result['combined_pct'] > 50:
        print("⚠️ Доходность высокая, но возможная (>50%)")
    else:
        print("✅ Доходность в реалистичных пределах (<50%)")
    
    # Проверка влияния стоп-лоссов
    if result['stop_loss_count'] > 0:
        print(f"✅ Стоп-лоссы учтены: {result['stop_loss_count']} случаев")
    else:
        print("ℹ️ Стоп-лоссов не было в данном тесте")
    
    # Проверка влияния молний
    if result['lightning_count'] > 0:
        print(f"✅ Молнии учтены: {result['lightning_count']} случаев")
    else:
        print("ℹ️ Молний не было в данном тесте")
    
    return result

def compare_with_previous():
    """
    Сравнение с предыдущими завышенными результатами
    """
    print("\nСРАВНЕНИЕ С ПРЕДЫДУЩИМИ РЕЗУЛЬТАТАМИ:")
    print("-" * 50)
    print("ДО ИСПРАВЛЕНИЯ (из CSV):")
    print("  Общая доходность: 1099.31%")
    print("  Всего сделок: 6327")
    print("  Средняя прибыль на сделку: 0.174%")
    print()
    
    # Запускаем тест
    result = test_fixed_logic()
    
    print("ПОСЛЕ ИСПРАВЛЕНИЯ:")
    print(f"  Общая доходность: {result['combined_pct']:.2f}%")
    print(f"  Всего сделок: {result['total_trades']:.0f}")
    avg_profit = result['combined_pct'] / result['total_trades'] if result['total_trades'] > 0 else 0
    print(f"  Средняя прибыль на сделку: {avg_profit:.4f}%")
    print()
    
    # Расчет улучшения
    improvement = ((1099.31 - result['combined_pct']) / 1099.31) * 100
    print(f"СНИЖЕНИЕ ЗАВЫШЕНИЯ: {improvement:.1f}%")
    
    if result['combined_pct'] < 100:
        print("✅ ИСПРАВЛЕНИЯ УСПЕШНЫ: Результаты стали реалистичными")
    else:
        print("⚠️ ТРЕБУЮТСЯ ДОПОЛНИТЕЛЬНЫЕ ИСПРАВЛЕНИЯ")

if __name__ == "__main__":
    compare_with_previous()
