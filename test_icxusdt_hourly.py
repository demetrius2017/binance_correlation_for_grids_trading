#!/usr/bin/env python3
"""
Тест ICXUSDT с часовыми данными для более точной симуляции сеточной торговли.
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector
from binance.client import Client

def test_icxusdt_hourly():
    """
    Тестирует ICXUSDT с часовыми данными для более реалистичной симуляции.
    """
    print("ТЕСТ ICXUSDT С ЧАСОВЫМИ ДАННЫМИ")
    print("="*80)
    
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        # Получаем часовые данные за 7 дней (168 часов)
        print("Получение часовых данных для ICXUSDT за 7 дней...")
        df_hourly = collector.get_historical_data("ICXUSDT", Client.KLINE_INTERVAL_1HOUR, 168)
        
        if df_hourly.empty:
            print("❌ Не удалось получить часовые данные для ICXUSDT")
            return
            
        print(f"✅ Получено {len(df_hourly)} часов данных")
        print(f"Период: {df_hourly.index[0].strftime('%Y-%m-%d %H:%M')} - {df_hourly.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print(f"Начальная цена: ${df_hourly.iloc[0]['close']:.6f}")
        print(f"Конечная цена: ${df_hourly.iloc[-1]['close']:.6f}")
        print(f"Изменение цены: {((df_hourly.iloc[-1]['close'] / df_hourly.iloc[0]['close']) - 1) * 100:.2f}%")
        print(f"Максимум: ${df_hourly['high'].max():.6f}")
        print(f"Минимум: ${df_hourly['low'].min():.6f}")
        print()
        
        # Расчет среднего часового диапазона
        hourly_ranges = (df_hourly['high'] - df_hourly['low']) / df_hourly['low'] * 100
        avg_hourly_range = hourly_ranges.mean()
        print(f"Средний часовой диапазон: {avg_hourly_range:.3f}%")
        print()
        
        # Для сравнения получаем дневные данные за тот же период
        print("Получение дневных данных для сравнения...")
        df_daily = collector.get_historical_data("ICXUSDT", Client.KLINE_INTERVAL_1DAY, 7)
        daily_ranges = (df_daily['high'] - df_daily['low']) / df_daily['low'] * 100
        avg_daily_range = daily_ranges.mean()
        print(f"Средний дневной диапазон: {avg_daily_range:.2f}%")
        print()
        
        # Тестируем разные диапазоны сетки - адаптированные под часовые данные
        print("РЕЗУЛЬТАТЫ СИМУЛЯЦИИ С ЧАСОВЫМИ ДАННЫМИ:")
        print("="*110)
        print(f"{'Диапазон':>8} | {'Покрытие ч.':>12} | {'Стоп-лосс':>10} | {'Стратегия':>15} | {'Симул. PnL':>12} | {'Long PnL':>10} | {'Short PnL':>11} | {'Молнии':>8} | {'Стоп-лоссы':>10}")
        print("-" * 110)
        
        # Тестируем меньшие диапазоны, подходящие для часовых данных
        grid_ranges = [1, 2, 3, 5, 8]  # Меньшие диапазоны для часовых данных
        
        results_hourly = []
        
        for grid_range in grid_ranges:
            # Покрытие часовых колебаний
            hourly_coverage = min(grid_range / avg_hourly_range * 100, 100)
            
            for stop_loss in [2, 5]:  # Меньшие стоп-лоссы для часовых данных
                for close_both in [False, True]:
                    strategy_name = "Закрыть обе" if close_both else "Независимые"
                    
                    # Симуляция с часовыми данными
                    result = analyzer.estimate_dual_grid_by_candles(
                        df_hourly,
                        grid_range_pct=grid_range,
                        grid_step_pct=0.3,  # Меньший шаг для часовых данных
                        commission_pct=0.1,
                        stop_loss_pct=stop_loss,
                        stop_loss_coverage=0.5,
                        close_both_on_stop_loss=close_both
                    )
                    
                    results_hourly.append({
                        'grid_range': grid_range,
                        'hourly_coverage': hourly_coverage,
                        'stop_loss': stop_loss,
                        'strategy': strategy_name,
                        'simulation_pnl': result['combined_pct'],
                        'long_pnl': result['long_pct'],
                        'short_pnl': result['short_pct'],
                        'lightning_breaks': result['lightning_breaks'],
                        'total_stop_losses': result['long_stop_losses'] + result['short_stop_losses']
                    })
                    
                    print(f"{grid_range:>8.0f} | {hourly_coverage:>12.1f} | {stop_loss:>10.0f} | {strategy_name:>15} | "
                          f"{result['combined_pct']:>12.2f} | {result['long_pct']:>10.2f} | "
                          f"{result['short_pct']:>11.2f} | {result['lightning_breaks']:>8d} | "
                          f"{result['long_stop_losses'] + result['short_stop_losses']:>10d}")
        
        print()
        
        # Анализ лучших результатов
        print("АНАЛИЗ РЕЗУЛЬТАТОВ С ЧАСОВЫМИ ДАННЫМИ:")
        print("="*80)
        
        best_hourly = max(results_hourly, key=lambda x: x['simulation_pnl'])
        print(f"Лучший результат: {best_hourly['simulation_pnl']:.2f}% за 7 дней")
        print(f"Параметры: диапазон {best_hourly['grid_range']}%, стоп-лосс {best_hourly['stop_loss']}%, {best_hourly['strategy']}")
        print(f"Покрытие часовых колебаний: {best_hourly['hourly_coverage']:.1f}%")
        
        # Пересчет в месячную доходность
        weekly_profit = best_hourly['simulation_pnl']
        monthly_profit = weekly_profit * 4.3  # 4.3 недели в месяце
        print(f"Прогнозируемая месячная доходность: {monthly_profit:.1f}%")
        print()
        
        # Сравнение с дневными данными
        print("СРАВНЕНИЕ ЧАСОВЫХ И ДНЕВНЫХ ДАННЫХ:")
        print("="*80)
        
        # Тестируем на дневных данных с похожими параметрами
        print("Результаты с дневными данными (диапазон 5%, стоп-лосс 5%):")
        result_daily = analyzer.estimate_dual_grid_by_candles(
            df_daily,
            grid_range_pct=5.0,
            grid_step_pct=1.0,
            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            close_both_on_stop_loss=False
        )
        print(f"  Дневные данные: {result_daily['combined_pct']:.2f}% за 7 дней")
        
        print("Результаты с часовыми данными (диапазон 5%, стоп-лосс 5%):")
        result_hourly_5 = [r for r in results_hourly if r['grid_range'] == 5 and r['stop_loss'] == 5 and r['strategy'] == 'Независимые'][0]
        print(f"  Часовые данные: {result_hourly_5['simulation_pnl']:.2f}% за 7 дней")
        
        print(f"  Разница: {result_hourly_5['simulation_pnl'] - result_daily['combined_pct']:.2f}%")
        
        if abs(result_hourly_5['simulation_pnl'] - result_daily['combined_pct']) > 10:
            print("⚠️  Значительная разница между часовыми и дневными данными!")
        else:
            print("✅ Результаты примерно одинаковые")
        
        # Анализ частоты молний
        print(f"\nАНАЛИЗ МОЛНИЙ:")
        print(f"Часовые данные - больше точек для анализа:")
        print(f"  Среднее количество молний: {sum(r['lightning_breaks'] for r in results_hourly) / len(results_hourly):.1f}")
        print(f"  Средний диапазон покрытия: {sum(r['hourly_coverage'] for r in results_hourly) / len(results_hourly):.1f}%")
        
        # Рекомендации
        print(f"\nРЕКОМЕНДАЦИИ ДЛЯ ЧАСОВЫХ ДАННЫХ:")
        optimal_results = [r for r in results_hourly if r['simulation_pnl'] > 0]
        if optimal_results:
            print("✅ Найдены прибыльные параметры:")
            for r in sorted(optimal_results, key=lambda x: x['simulation_pnl'], reverse=True)[:3]:
                print(f"  Диапазон {r['grid_range']}%, стоп-лосс {r['stop_loss']}%, {r['strategy']}: {r['simulation_pnl']:.2f}%")
        else:
            print("❌ Все протестированные параметры убыточны")
            print("   Рекомендуется увеличить диапазон сетки или уменьшить стоп-лосс")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_icxusdt_hourly()
