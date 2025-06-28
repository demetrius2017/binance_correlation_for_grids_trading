"""
Тест логики перестроения сетки с оставшимся балансом
"""

def test_grid_reset_logic():
    """Тестирует логику перестроения сетки с учетом оставшегося баланса"""
    
    print("=== ТЕСТ ЛОГИКИ ПЕРЕСТРОЕНИЯ СЕТКИ ===\n")
    
    # Начальные параметры
    initial_balance = 1000.0
    grid_step_pct = 2.0
    
    # Имитируем ситуацию до срабатывания стоп-лосса
    print("📊 ИЗНАЧАЛЬНАЯ СИТУАЦИЯ:")
    num_levels = int(20.0 / grid_step_pct)  # 20% диапазон / 2% шаг = 10 уровней
    final_order_size = initial_balance / num_levels  # $1000 / 10 = $100 за ордер
    
    print(f"   • Начальный баланс: ${initial_balance:.2f}")
    print(f"   • Количество уровней: {num_levels}")
    print(f"   • Размер ордера: ${final_order_size:.2f}")
    
    # Имитируем срабатывание стоп-лосса (потеря 30% баланса)
    print("\n🔥 СРАБАТЫВАНИЕ СТОП-ЛОССА:")
    balance_after_stop_loss = initial_balance * 0.7  # Осталось 70% от баланса
    print(f"   • Баланс после стоп-лосса: ${balance_after_stop_loss:.2f}")
    print(f"   • Потеряно: ${initial_balance - balance_after_stop_loss:.2f} ({((initial_balance - balance_after_stop_loss) / initial_balance * 100):.1f}%)")
    
    # СТАРАЯ ЛОГИКА (неправильная)
    print("\n❌ СТАРАЯ ЛОГИКА (неправильная):")
    print("   • Использует изначальный размер ордера: $100.00")
    print("   • При балансе $700 можно разместить только 7 ордеров")
    print("   • НО логика все равно пытается разместить 10 ордеров!")
    print("   • Результат: недостаток средств или мелкие ордера")
    
    # НОВАЯ ЛОГИКА (правильная)
    print("\n✅ НОВАЯ ЛОГИКА (правильная):")
    if balance_after_stop_loss > 0 and final_order_size > 0:
        num_levels_new = max(1, int(balance_after_stop_loss / final_order_size))
        final_order_size_new = balance_after_stop_loss / num_levels_new
        
        print(f"   • Пересчитанное количество уровней: {num_levels_new}")
        print(f"   • Новый размер ордера: ${final_order_size_new:.2f}")
        print(f"   • Общий используемый баланс: ${num_levels_new * final_order_size_new:.2f}")
        print(f"   • Резерв: ${balance_after_stop_loss - (num_levels_new * final_order_size_new):.2f}")
    
    print("\n🎯 ПРЕИМУЩЕСТВА НОВОЙ ЛОГИКИ:")
    print("   ✅ Использует весь доступный баланс")
    print("   ✅ Пропорциональные размеры ордеров")
    print("   ✅ Оптимальное количество уровней")
    print("   ✅ Защита от переполнения")
    
    # Демонстрация с разными уровнями потерь
    print("\n📈 ТЕСТ С РАЗНЫМИ УРОВНЯМИ ПОТЕРЬ:")
    for loss_pct in [10, 30, 50, 70, 90]:
        remaining_balance = initial_balance * (1 - loss_pct / 100)
        if remaining_balance > 0:
            num_levels_test = max(1, int(remaining_balance / final_order_size))
            order_size_test = remaining_balance / num_levels_test
            print(f"   • Потеря {loss_pct:2d}%: баланс ${remaining_balance:6.2f} → {num_levels_test:2d} уровней × ${order_size_test:6.2f}")
        else:
            print(f"   • Потеря {loss_pct:2d}%: торговля остановлена")

if __name__ == "__main__":
    test_grid_reset_logic()
