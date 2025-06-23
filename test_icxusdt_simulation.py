#!/usr/bin/env python3
"""
Тест симуляционной доходности для ICXUSDT с новой логикой.
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector

def test_icxusdt_simulation():
    """
    Тестирует симуляционную доходность для ICXUSDT.
    """
    print("ТЕСТ СИМУЛЯЦИОННОЙ ДОХОДНОСТИ ДЛЯ ICXUSDT")
    print("="*80)
      # Инициализация
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        # Получаем данные для ICXUSDT
        print("Получение данных для ICXUSDT...")
        df = collector.get_historical_data("ICXUSDT", "1d", 30)
        
        if df.empty:
            print("❌ Не удалось получить данные для ICXUSDT")
            return
            
        print(f"✅ Получено {len(df)} дней данных")
        print(f"Период: {df.index[0].strftime('%Y-%m-%d')} - {df.index[-1].strftime('%Y-%m-%d')}")
        print(f"Начальная цена: ${df.iloc[0]['close']:.6f}")
        print(f"Конечная цена: ${df.iloc[-1]['close']:.6f}")
        print(f"Изменение цены: {((df.iloc[-1]['close'] / df.iloc[0]['close']) - 1) * 100:.2f}%")
        print(f"Максимум: ${df['high'].max():.6f}")
        print(f"Минимум: ${df['low'].min():.6f}")
        print()
        
        # Расчет среднего дневного диапазона
        daily_ranges = (df['high'] - df['low']) / df['low'] * 100
        avg_daily_range = daily_ranges.mean()
        print(f"Средний дневной диапазон: {avg_daily_range:.2f}%")
        print()
        
        # Тестируем разные диапазоны сетки
        grid_ranges = [3, 6, 10, 15, 20]
        stop_loss_values = [5, 10]  # 5% и 10% стоп-лосс
        
        print("РЕЗУЛЬТАТЫ СИМУЛЯЦИИ:")
        print("="*100)
        print(f"{'Диапазон':>8} | {'Стоп-лосс':>10} | {'Стратегия':>15} | {'Симул. PnL':>12} | {'Long PnL':>10} | {'Short PnL':>11} | {'Молнии':>8} | {'Стоп-лоссы':>10}")
        print("-" * 100)
        
        results = []
        
        for grid_range in grid_ranges:
            for stop_loss in stop_loss_values:
                for close_both in [False, True]:
                    strategy_name = "Закрыть обе" if close_both else "Независимые"
                    
                    # Симуляция
                    result = analyzer.estimate_dual_grid_by_candles(
                        df,
                        grid_range_pct=grid_range,
                        grid_step_pct=1.0,
                        commission_pct=0.1,
                        stop_loss_pct=stop_loss,
                        stop_loss_coverage=0.5,  # 50% покрытие
                        close_both_on_stop_loss=close_both
                    )
                    
                    results.append({
                        'grid_range': grid_range,
                        'stop_loss': stop_loss,
                        'strategy': strategy_name,
                        'simulation_pnl': result['combined_pct'],
                        'long_pnl': result['long_pct'],
                        'short_pnl': result['short_pct'],
                        'lightning_breaks': result['lightning_breaks'],
                        'total_stop_losses': result['long_stop_losses'] + result['short_stop_losses'],
                        'long_active': result['long_grid_final_state'],
                        'short_active': result['short_grid_final_state']
                    })
                    
                    print(f"{grid_range:>8.0f} | {stop_loss:>10.0f} | {strategy_name:>15} | "
                          f"{result['combined_pct']:>12.2f} | {result['long_pct']:>10.2f} | "
                          f"{result['short_pct']:>11.2f} | {result['lightning_breaks']:>8d} | "
                          f"{result['long_stop_losses'] + result['short_stop_losses']:>10d}")
        
        print()
        
        # Анализ лучших результатов
        print("АНАЛИЗ РЕЗУЛЬТАТОВ:")
        print("="*80)
        
        # Группируем по стоп-лоссу
        for stop_loss in stop_loss_values:
            print(f"\nСтоп-лосс {stop_loss}%:")
            
            stop_loss_results = [r for r in results if r['stop_loss'] == stop_loss]
            
            # Лучший результат для каждой стратегии
            independent_results = [r for r in stop_loss_results if r['strategy'] == 'Независимые']
            close_both_results = [r for r in stop_loss_results if r['strategy'] == 'Закрыть обе']
            
            if independent_results:
                best_independent = max(independent_results, key=lambda x: x['simulation_pnl'])
                print(f"  Лучший результат (Независимые): {best_independent['simulation_pnl']:.2f}% "
                      f"при диапазоне {best_independent['grid_range']}%")
            
            if close_both_results:
                best_close_both = max(close_both_results, key=lambda x: x['simulation_pnl'])
                print(f"  Лучший результат (Закрыть обе): {best_close_both['simulation_pnl']:.2f}% "
                      f"при диапазоне {best_close_both['grid_range']}%")
        
        # Сравнение стоп-лоссов
        print(f"\nСРАВНЕНИЕ СТОП-ЛОССОВ:")
        
        # Берем лучшие результаты для каждого стоп-лосса
        best_5_percent = max([r for r in results if r['stop_loss'] == 5], key=lambda x: x['simulation_pnl'])
        best_10_percent = max([r for r in results if r['stop_loss'] == 10], key=lambda x: x['simulation_pnl'])
        
        print(f"Лучший результат со стоп-лоссом 5%: {best_5_percent['simulation_pnl']:.2f}% "
              f"(диапазон {best_5_percent['grid_range']}%, {best_5_percent['strategy']})")
        print(f"Лучший результат со стоп-лоссом 10%: {best_10_percent['simulation_pnl']:.2f}% "
              f"(диапазон {best_10_percent['grid_range']}%, {best_10_percent['strategy']})")
        
        difference = best_10_percent['simulation_pnl'] - best_5_percent['simulation_pnl']
        print(f"Разница: {difference:.2f}% в пользу стоп-лосса {10 if difference > 0 else 5}%")
        
        # Проверка покрытия колебаний
        print(f"\nПОКРЫТИЕ КОЛЕБАНИЙ:")
        for grid_range in [3, 6, 10, 15, 20]:
            coverage = min(grid_range / avg_daily_range * 100, 100)
            print(f"Диапазон {grid_range}%: покрытие {coverage:.1f}% ({'✅' if coverage >= 80 else '⚠️' if coverage >= 60 else '❌'})")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_icxusdt_simulation()
