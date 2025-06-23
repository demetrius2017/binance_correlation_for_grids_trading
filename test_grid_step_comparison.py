#!/usr/bin/env python3
"""
Сравнение шагов сетки 0.3% vs 0.8% на часовых данных ICXUSDT.
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector
from binance.client import Client

def compare_grid_steps():
    """
    Сравнивает результаты с разными шагами сетки на часовых данных.
    """
    print("СРАВНЕНИЕ ШАГОВ СЕТКИ: 0.3% vs 0.8% НА ЧАСОВЫХ ДАННЫХ")
    print("="*80)
    
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        # Получаем часовые данные за 7 дней
        print("Получение часовых данных для ICXUSDT за 7 дней...")
        df_hourly = collector.get_historical_data("ICXUSDT", Client.KLINE_INTERVAL_1HOUR, 168)
        
        if df_hourly.empty:
            print("❌ Не удалось получить часовые данные")
            return
            
        print(f"✅ Получено {len(df_hourly)} часов данных")
        print(f"Период: {df_hourly.index[0].strftime('%Y-%m-%d %H:%M')} - {df_hourly.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print(f"Изменение цены: {((df_hourly.iloc[-1]['close'] / df_hourly.iloc[0]['close']) - 1) * 100:.2f}%")
        
        hourly_ranges = (df_hourly['high'] - df_hourly['low']) / df_hourly['low'] * 100
        avg_hourly_range = hourly_ranges.mean()
        print(f"Средний часовой диапазон: {avg_hourly_range:.3f}%")
        print()
        
        # Тестируемые параметры
        grid_ranges = [3, 5, 8]
        stop_losses = [2, 5]
        grid_steps = [0.3, 0.8]  # Сравниваем два шага
        
        print("РЕЗУЛЬТАТЫ С РАЗНЫМИ ШАГАМИ СЕТКИ:")
        print("="*130)
        print(f"{'Диапазон':>8} | {'Шаг':>6} | {'Стоп-лосс':>10} | {'Стратегия':>15} | {'Симул. PnL':>12} | {'Long PnL':>10} | {'Short PnL':>11} | {'Молнии':>8} | {'Стоп-лоссы':>10}")
        print("-" * 130)
        
        results = []
        
        for grid_range in grid_ranges:
            for grid_step in grid_steps:
                for stop_loss in stop_losses:
                    for close_both in [False, True]:
                        strategy_name = "Закрыть обе" if close_both else "Независимые"
                        
                        # Симуляция
                        result = analyzer.estimate_dual_grid_by_candles(
                            df_hourly,
                            grid_range_pct=grid_range,
                            grid_step_pct=grid_step,
                            commission_pct=0.1,
                            stop_loss_pct=stop_loss,
                            stop_loss_coverage=0.5,
                            close_both_on_stop_loss=close_both
                        )
                        
                        results.append({
                            'grid_range': grid_range,
                            'grid_step': grid_step,
                            'stop_loss': stop_loss,
                            'strategy': strategy_name,
                            'simulation_pnl': result['combined_pct'],
                            'long_pnl': result['long_pct'],
                            'short_pnl': result['short_pct'],
                            'lightning_breaks': result['lightning_breaks'],
                            'total_stop_losses': result['long_stop_losses'] + result['short_stop_losses']
                        })
                        
                        print(f"{grid_range:>8.0f} | {grid_step:>6.1f} | {stop_loss:>10.0f} | {strategy_name:>15} | "
                              f"{result['combined_pct']:>12.2f} | {result['long_pct']:>10.2f} | "
                              f"{result['short_pct']:>11.2f} | {result['lightning_breaks']:>8d} | "
                              f"{result['long_stop_losses'] + result['short_stop_losses']:>10d}")
        
        print()
        
        # Анализ по шагам
        print("АНАЛИЗ ПО ШАГАМ СЕТКИ:")
        print("="*80)
        
        for grid_step in grid_steps:
            step_results = [r for r in results if r['grid_step'] == grid_step]
            best_result = max(step_results, key=lambda x: x['simulation_pnl'])
            avg_result = sum(r['simulation_pnl'] for r in step_results) / len(step_results)
            profitable_count = len([r for r in step_results if r['simulation_pnl'] > 0])
            
            print(f"Шаг {grid_step}%:")
            print(f"  Лучший результат: {best_result['simulation_pnl']:.2f}% "
                  f"(диапазон {best_result['grid_range']}%, стоп-лосс {best_result['stop_loss']}%, {best_result['strategy']})")
            print(f"  Средний результат: {avg_result:.2f}%")
            print(f"  Прибыльных комбинаций: {profitable_count}/{len(step_results)}")
            
            # Месячная экстраполяция лучшего результата
            monthly_profit = best_result['simulation_pnl'] * 4.3
            print(f"  Прогноз месячной доходности: {monthly_profit:.1f}%")
            print()
        
        # Прямое сравнение одинаковых параметров
        print("ПРЯМОЕ СРАВНЕНИЕ ОДИНАКОВЫХ ПАРАМЕТРОВ:")
        print("="*80)
        
        # Сравним лучшие параметры с разными шагами
        test_combinations = [
            (5, 2, "Независимые"),
            (5, 2, "Закрыть обе"),
            (8, 2, "Независимые"),
            (3, 5, "Независимые")
        ]
        
        for grid_range, stop_loss, strategy in test_combinations:
            result_03 = next((r for r in results if r['grid_range'] == grid_range and 
                             r['stop_loss'] == stop_loss and r['strategy'] == strategy and 
                             r['grid_step'] == 0.3), None)
            result_08 = next((r for r in results if r['grid_range'] == grid_range and 
                             r['stop_loss'] == stop_loss and r['strategy'] == strategy and 
                             r['grid_step'] == 0.8), None)
            
            if result_03 and result_08:
                difference = result_08['simulation_pnl'] - result_03['simulation_pnl']
                print(f"Диапазон {grid_range}%, стоп-лосс {stop_loss}%, {strategy}:")
                print(f"  Шаг 0.3%: {result_03['simulation_pnl']:6.2f}%")
                print(f"  Шаг 0.8%: {result_08['simulation_pnl']:6.2f}%")
                print(f"  Разница:   {difference:6.2f}% ({'👍' if difference > 0 else '👎' if difference < -1 else '🤷'})")
                print()
        
        # Общие выводы
        print("ОБЩИЕ ВЫВОДЫ:")
        print("="*80)
        
        step_03_results = [r for r in results if r['grid_step'] == 0.3]
        step_08_results = [r for r in results if r['grid_step'] == 0.8]
        
        best_03 = max(step_03_results, key=lambda x: x['simulation_pnl'])
        best_08 = max(step_08_results, key=lambda x: x['simulation_pnl'])
        
        avg_03 = sum(r['simulation_pnl'] for r in step_03_results) / len(step_03_results)
        avg_08 = sum(r['simulation_pnl'] for r in step_08_results) / len(step_08_results)
        
        print(f"Лучший результат с шагом 0.3%: {best_03['simulation_pnl']:.2f}%")
        print(f"Лучший результат с шагом 0.8%: {best_08['simulation_pnl']:.2f}%")
        print(f"Преимущество шага {0.3 if best_03['simulation_pnl'] > best_08['simulation_pnl'] else 0.8}%: "
              f"{abs(best_03['simulation_pnl'] - best_08['simulation_pnl']):.2f}%")
        print()
        
        print(f"Средний результат с шагом 0.3%: {avg_03:.2f}%")
        print(f"Средний результат с шагом 0.8%: {avg_08:.2f}%")
        print(f"Преимущество по среднему: {abs(avg_03 - avg_08):.2f}% в пользу шага {0.3 if avg_03 > avg_08 else 0.8}%")
        print()
        
        # Рекомендации
        if best_03['simulation_pnl'] > best_08['simulation_pnl']:
            print("🎯 РЕКОМЕНДАЦИЯ: Шаг 0.3% показывает лучшие результаты")
            print(f"   Оптимальные параметры: диапазон {best_03['grid_range']}%, стоп-лосс {best_03['stop_loss']}%, {best_03['strategy']}")
        else:
            print("🎯 РЕКОМЕНДАЦИЯ: Шаг 0.8% показывает лучшие результаты")
            print(f"   Оптимальные параметры: диапазон {best_08['grid_range']}%, стоп-лосс {best_08['stop_loss']}%, {best_08['strategy']}")
        
        # Анализ влияния на молнии
        avg_lightning_03 = sum(r['lightning_breaks'] for r in step_03_results) / len(step_03_results)
        avg_lightning_08 = sum(r['lightning_breaks'] for r in step_08_results) / len(step_08_results)
        
        print(f"\nВлияние на частоту молний:")
        print(f"  Среднее количество молний (шаг 0.3%): {avg_lightning_03:.1f}")
        print(f"  Среднее количество молний (шаг 0.8%): {avg_lightning_08:.1f}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_grid_steps()
