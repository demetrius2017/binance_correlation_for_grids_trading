"""
Тестовый скрипт для проверки логики переноса параметров из оптимизации в Grid Trading
"""

# Имитируем session_state Streamlit
class MockSessionState:
    def __init__(self):
        self.transfer_params = None

def test_transfer_logic():
    """Тестируем логику переноса параметров"""
    
    # Создаем mock session_state
    session_state = MockSessionState()
    
    # Имитируем данные результата оптимизации
    mock_optimization_result = {
        'grid_range_pct': 25.0,
        'grid_step_pct': 1.5,
        'stop_loss_pct': 30.0,
        'combined_score': 12.34
    }
    
    mock_optimization_params = {
        'pair': 'BTCUSDT',
        'balance': 5000,
        'timeframe': '4h',
        'days': 180
    }
    
    # Имитируем сохранение параметров для переноса (как в app.py)
    session_state.transfer_params = {
        'pair': mock_optimization_params['pair'],
        'grid_range_pct': mock_optimization_result['grid_range_pct'],
        'grid_step_pct': mock_optimization_result['grid_step_pct'],
        'stop_loss_pct': mock_optimization_result['stop_loss_pct'],
        'initial_balance': mock_optimization_params['balance'],
        'timeframe': mock_optimization_params['timeframe'],
        'simulation_days': mock_optimization_params['days'],
        'source': f"Тест (скор: {mock_optimization_result['combined_score']:.2f}%)"
    }
    
    # Проверяем, что параметры сохранились корректно
    assert session_state.transfer_params is not None, "transfer_params должен быть установлен"
    
    # Имитируем логику автозаполнения (как в Grid Trading вкладке)
    default_grid_range = session_state.transfer_params['grid_range_pct'] if session_state.transfer_params else 20.0
    default_grid_step = session_state.transfer_params['grid_step_pct'] if session_state.transfer_params else 1.0  
    default_balance = session_state.transfer_params['initial_balance'] if session_state.transfer_params else 1000
    default_days = session_state.transfer_params['simulation_days'] if session_state.transfer_params else 90
    default_stop_loss = session_state.transfer_params['stop_loss_pct'] if session_state.transfer_params else 25.0
    default_timeframe = session_state.transfer_params['timeframe'] if session_state.transfer_params else "1h"
    default_pair = session_state.transfer_params['pair'] if session_state.transfer_params else "ETHUSDT"
    
    # Проверяем, что значения по умолчанию установлены корректно
    assert default_grid_range == 25.0, f"Ожидается 25.0, получено {default_grid_range}"
    assert default_grid_step == 1.5, f"Ожидается 1.5, получено {default_grid_step}"
    assert default_balance == 5000, f"Ожидается 5000, получено {default_balance}"
    assert default_days == 180, f"Ожидается 180, получено {default_days}"
    assert default_stop_loss == 30.0, f"Ожидается 30.0, получено {default_stop_loss}"
    assert default_timeframe == "4h", f"Ожидается '4h', получено '{default_timeframe}'"
    assert default_pair == "BTCUSDT", f"Ожидается 'BTCUSDT', получено '{default_pair}'"
    
    print("✅ Все тесты пройдены!")
    print(f"📊 Перенесенные параметры:")
    print(f"   • Пара: {default_pair}")
    print(f"   • Диапазон сетки: {default_grid_range:.1f}%")
    print(f"   • Шаг сетки: {default_grid_step:.2f}%")
    print(f"   • Стоп-лосс: {default_stop_loss:.1f}%")
    print(f"   • Баланс: {default_balance} USDT")
    print(f"   • Таймфрейм: {default_timeframe}")
    print(f"   • Период: {default_days} дней")
    print(f"   • Источник: {session_state.transfer_params['source']}")

if __name__ == "__main__":
    test_transfer_logic()
