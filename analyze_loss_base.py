#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ расчета убытков в Grid Trading - от какой суммы считаются проценты
"""

def analyze_loss_calculation():
    """
    Анализирует, что означают проценты убытков в симуляции
    """
    print("=== АНАЛИЗ РАСЧЕТА УБЫТКОВ В GRID TRADING ===")
    print()
    
    print("ТЕКУЩАЯ ЛОГИКА В КОДЕ:")
    print("-" * 40)
    print("1. body_pct = abs(close_p - open_p) / base_price * 100")
    print("   где base_price = min(open_p, close_p)")
    print()
    print("2. При стоп-лоссе:")
    print("   actual_loss = body_pct")
    print("   total_long_pnl -= actual_loss")
    print()
    
    print("ПРИМЕР РАСЧЕТА:")
    print("-" * 20)
    open_price = 1.000
    close_price = 0.946  # Падение на ~5.4%
    
    base_price = min(open_price, close_price)  # 0.946
    body_pct = abs(close_price - open_price) / base_price * 100
    
    print(f"Open: ${open_price:.3f}")
    print(f"Close: ${close_price:.3f}")
    print(f"base_price (min): ${base_price:.3f}")
    print(f"body_pct: {body_pct:.2f}%")
    print()
    
    # Альтернативные расчеты
    decline_from_open = (open_price - close_price) / open_price * 100
    print(f"Альтернативный расчет (от open): {decline_from_open:.2f}%")
    print()
    
    print("ЧТО ЭТО ОЗНАЧАЕТ В КОНТЕКСТЕ GRID TRADING:")
    print("-" * 50)
    print("❓ ПРОБЛЕМА: Проценты считаются от ЦЕНЫ, а не от КАПИТАЛА")
    print()
    print("В Grid Trading:")
    print("- У нас есть определенный капитал (например, $1000)")
    print("- Мы размещаем ордера в сетке")
    print("- При стоп-лоссе мы теряем часть КАПИТАЛА, а не цены")
    print()
    
    print("ПРИМЕР С КАПИТАЛОМ:")
    print("-" * 25)
    initial_capital = 1000  # $1000 капитал
    grid_investment_per_side = 500  # $500 на каждую сетку
    
    print(f"Начальный капитал: ${initial_capital}")
    print(f"Инвестиция в Long сетку: ${grid_investment_per_side}")
    print()
    
    # При падении цены на 5.4%
    price_decline_pct = 5.4
    
    # В реальности потери зависят от:
    # 1. Сколько позиций было открыто
    # 2. На каких уровнях они были открыты
    # 3. Сколько капитала было задействовано
    
    print("РЕАЛЬНАЯ ЛОГИКА УБЫТКОВ:")
    print("Если цена упала на 5.4%, то убыток Long сетки зависит от:")
    print("1. Количества открытых Long позиций")
    print("2. Среднего уровня входа")
    print("3. Размера позиций")
    print()
    
    # Примерный расчет
    avg_entry_level = 0.98  # Средний уровень входа (2% ниже начальной цены)
    current_price = 0.946
    position_size = 300  # $300 в Long позициях
    
    real_loss_pct = (avg_entry_level - current_price) / avg_entry_level * 100
    real_loss_amount = position_size * (real_loss_pct / 100)
    capital_loss_pct = real_loss_amount / initial_capital * 100
    
    print(f"Пример реального расчета:")
    print(f"- Средний уровень входа: ${avg_entry_level:.3f}")
    print(f"- Текущая цена: ${current_price:.3f}")
    print(f"- Убыток по позициям: {real_loss_pct:.2f}%")
    print(f"- Размер позиций: ${position_size}")
    print(f"- Убыток в долларах: ${real_loss_amount:.2f}")
    print(f"- Убыток от капитала: {capital_loss_pct:.2f}%")
    print()

def analyze_current_implementation():
    """
    Анализирует текущую реализацию в коде
    """
    print("=== ПРОБЛЕМЫ ТЕКУЩЕЙ РЕАЛИЗАЦИИ ===")
    print()
    
    print("🚨 ПРОБЛЕМА 1: НЕКОРРЕКТНАЯ БАЗА РАСЧЕТА")
    print("- body_pct считается от цены свечи")
    print("- total_long_pnl -= body_pct вычитает проценты от цены")
    print("- НО total_long_pnl аккумулирует проценты прибыли от капитала")
    print("- Смешивание разных баз расчета!")
    print()
    
    print("🚨 ПРОБЛЕМА 2: НЕЯСНАЯ ИНТЕРПРЕТАЦИЯ")
    print("- Что означает 'Long доходность: 536.30%'?")
    print("- 536% от какой суммы?")
    print("- От начального капитала? От инвестированной суммы?")
    print()
    
    print("🚨 ПРОБЛЕМА 3: НАКОПЛЕНИЕ БЕЗ БАЗЫ")
    print("- total_long_pnl += long_wick_profit")
    print("- long_wick_profit = trades * (grid_step - commission)")
    print("- Но нет привязки к размеру капитала или позиций")
    print()

def recommend_fixes():
    """
    Рекомендации по исправлению
    """
    print("=== РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ ===")
    print()
    
    print("💡 РЕШЕНИЕ 1: ОПРЕДЕЛИТЬ БАЗУ РАСЧЕТА")
    print("- Четко определить: проценты от чего считаются")
    print("- Например: 'от начального капитала $1000'")
    print("- Или: 'от суммы, выделенной на каждую сетку'")
    print()
    
    print("💡 РЕШЕНИЕ 2: НОРМАЛИЗАЦИЯ К КАПИТАЛУ")
    print("- Ввести параметр initial_capital")
    print("- Все проценты считать от этого капитала")
    print("- Пример: 5% от $1000 = $50 убытка")
    print()
    
    print("💡 РЕШЕНИЕ 3: УТОЧНИТЬ ДОКУМЕНТАЦИЮ")
    print("- Добавить пояснения в интерфейс")
    print("- 'Доходность рассчитывается от условного капитала $1000'")
    print("- Или процент от изменения цены актива")
    print()
    
    print("ПРИМЕР ИСПРАВЛЕННОГО КОДА:")
    print("-" * 30)
    print("# Определяем базу расчета")
    print("BASE_CAPITAL = 1000  # $1000 условный капитал")
    print("GRID_ALLOCATION = 0.5  # 50% на каждую сетку")
    print()
    print("# При стоп-лоссе")
    print("price_decline_pct = body_pct")
    print("allocated_capital = BASE_CAPITAL * GRID_ALLOCATION")
    print("loss_amount = allocated_capital * (price_decline_pct / 100)")
    print("loss_as_pct_of_total = loss_amount / BASE_CAPITAL * 100")
    print("total_long_pnl -= loss_as_pct_of_total")

if __name__ == "__main__":
    analyze_loss_calculation()
    print()
    analyze_current_implementation()
    print()
    recommend_fixes()
