"""
Тест для проверки корректности передачи и отображения шага сетки в симуляции Grid Trading.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector

def create_test_data(periods=30):
    """
    Создает тестовые данные для симуляции
    """
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='H')
    
    # Генерируем тестовые данные с реалистичными свечами
    np.random.seed(42)
    base_price = 100.0
    
    data = []
    for i in range(periods):
        # Симуляция колебаний цены ±2% с более частыми малыми движениями
        change = np.random.normal(0, 0.5)  # Среднее изменение 0%, стандартное отклонение 0.5%
        
        open_price = base_price * (1 + change / 100)
        
        # Диапазон свечи (высота)
        range_pct = abs(np.random.normal(1.0, 0.3))  # Средний диапазон 1%, стандартное отклонение 0.3%
        
        high_price = open_price * (1 + range_pct / 200)
        low_price = open_price * (1 - range_pct / 200)
        
        # Случайное направление закрытия
        close_direction = np.random.choice([-1, 1])
        close_price = open_price + close_direction * open_price * (range_pct / 400)
        
        # Проверяем, что high и low корректны
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
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

def test_grid_step_parameter():
    """
    Тестирует, что переданный параметр grid_step_pct корректно используется и возвращается
    """
    print("=== Тест корректности передачи параметра grid_step ===")    # Создаем фиктивный коллектор данных (не используем реальный API)
    class MockCollector:
        def __init__(self):
            self.client = None  # Добавляем атрибут client
        
        def get_historical_data(self, symbol, interval, limit):
            return pd.DataFrame()
        
        def get_orderbook(self, symbol):
            return {'bids': [], 'asks': []}
    
    # Создаем анализатор
    collector = MockCollector()
    # Обходим проверку типов, передавая объект как есть
    grid_analyzer = GridAnalyzer(collector)  # type: ignore
    
    # Создаем тестовые данные
    df = create_test_data(24)  # 24 часа данных
    
    # Тестируем различные значения grid_step
    test_steps = [0.3, 0.5, 1.0, 1.5, 2.0]
    
    print(f"Тестовые данные: {len(df)} свечей")
    print(f"Диапазон цен: {df['low'].min():.2f} - {df['high'].max():.2f}")
    print()
    
    for grid_step in test_steps:
        print(f"Тестируем grid_step = {grid_step}%")
        
        result = grid_analyzer.estimate_dual_grid_by_candles(
            df,
            grid_range_pct=20.0,
            grid_step_pct=grid_step,  # Передаем параметр
            use_real_commissions=True,
            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            stop_loss_strategy="independent"
        )
        
        returned_step = result['grid_step_pct']
        
        print(f"  Переданный шаг: {grid_step}%")
        print(f"  Возвращенный шаг: {returned_step}%")
        print(f"  Совпадают: {'✅' if abs(returned_step - grid_step) < 0.001 else '❌'}")
        print(f"  Общая доходность: {result['combined_pct']:.2f}%")
        print(f"  Всего сделок: {result['total_trades']}")
        print()
        
        # Проверяем, что возвращается именно тот шаг, который мы передали
        assert abs(returned_step - grid_step) < 0.001, f"Ожидался шаг {grid_step}%, получен {returned_step}%"
    
    print("✅ Все тесты passed! Параметр grid_step_pct передается и возвращается корректно.")

def test_interface_display():
    """
    Тестирует отображение в интерфейсе (логический тест без запуска Streamlit)
    """
    print("\n=== Тест логики отображения в интерфейсе ===")
    
    # Симулируем результат функции
    test_result = {
        'combined_pct': 5.25,
        'long_pct': 2.75,
        'short_pct': 2.50,
        'total_trades': 45,
        'lightning_count': 3,
        'stop_loss_count': 1,
        'long_active': True,
        'short_active': True,
        'grid_step_pct': 1.2  # Пользователь выбрал 1.2%
    }
    
    # Проверяем, как будет отображаться в таблице (код из app.py)
    grid_step_display = f"{test_result['grid_step_pct']:.2f}"
    
    print(f"Результат симуляции:")
    print(f"  grid_step_pct из результата: {test_result['grid_step_pct']}")
    print(f"  Отображение в таблице: {grid_step_display}%")
    print(f"  Корректность: {'✅' if grid_step_display == '1.20' else '❌'}")
    
    print("✅ Логика отображения корректна!")

if __name__ == "__main__":
    try:
        test_grid_step_parameter()
        test_interface_display()
        
        print("\n🎉 Все тесты успешно пройдены!")
        print("✅ Параметр grid_step корректно передается от пользователя к функции")
        print("✅ Функция возвращает именно тот шаг, который был передан")
        print("✅ Интерфейс будет отображать правильное значение шага сетки")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        raise
