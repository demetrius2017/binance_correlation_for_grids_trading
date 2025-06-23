#!/usr/bin/env python3
"""
Тест ICXUSDT с периодом 90 дней для сравнения с интерфейсом.
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer
from modules.collector import BinanceDataCollector

def test_icxusdt_90_days():
    """
    Тестирует ICXUSDT с периодом 90 дней (как возможно в интерфейсе).
    """
    print("ТЕСТ ICXUSDT С ПЕРИОДОМ 90 ДНЕЙ")
    print("="*80)
    
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        # Получаем данные за 90 дней
        print("Получение данных для ICXUSDT за 90 дней...")
        df = collector.get_historical_data("ICXUSDT", "1d", 90)
        
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
          # Тестируем те же диапазоны что и в CSV
        grid_ranges = [3, 6, 10, 15]        
        print("РЕЗУЛЬТАТЫ СИМУЛЯЦИИ ЗА 90 ДНЕЙ (ЧАСОВЫЕ ДАННЫЕ, РЕАЛЬНЫЕ КОМИССИИ):")
        print("="*100)
        print(f"{'Диапазон':>8} | {'Стоп-лосс':>10} | {'Симул. PnL':>12} | {'Long PnL':>10} | {'Short PnL':>11} | {'Молнии':>8} | {'Стоп-лоссы':>10} | {'Сделки':>8}")
        print("-" * 100)
        
        results_90 = []
        
        # Получаем часовые данные для более точного тестирования прибыльности
        print("Получение часовых данных за 90 дней...")
        df_hourly = collector.get_historical_data("ICXUSDT", "1h", 90*24)  # 90 дней часовых данных
        
        if df_hourly.empty:
            print("❌ Не удалось получить часовые данные")
            return
            
        print(f"✅ Получено {len(df_hourly)} часовых свечей")
        print(f"Период: {df_hourly.index[0].strftime('%Y-%m-%d %H:%M')} - {df_hourly.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print()
        
        # Тестируем с реальными комиссиями на часовых данных
        for grid_range in grid_ranges:
            for stop_loss in [5, 10]:
                result = analyzer.estimate_dual_grid_by_candles(
                    df_hourly,  # Используем часовые данные
                    grid_range_pct=grid_range,
                    grid_step_pct=0.5,  # Оптимальный шаг для часовых данных
                    use_real_commissions=True,
                    stop_loss_pct=stop_loss,
                    stop_loss_coverage=0.5,
                    stop_loss_strategy="independent"  # Лучшая стратегия
                )
                results_90.append({
                    'grid_range': grid_range,
                    'stop_loss': stop_loss,
                    'simulation_pnl': result['combined_pct'],
                    'long_pnl': result['long_pct'],
                    'short_pnl': result['short_pct'],
                    'lightning_breaks': result['lightning_count'],
                    'total_stop_losses': result['stop_loss_count'],
                    'total_trades': result['total_trades'],
                    'maker_trades': result['long_maker_trades'] + result['short_maker_trades'],
                    'taker_trades': result['long_taker_trades'] + result['short_taker_trades']
                })                
                print(f"{grid_range:>8.0f} | {stop_loss:>10.0f} | "
                      f"{result['combined_pct']:>12.2f} | {result['long_pct']:>10.2f} | "
                      f"{result['short_pct']:>11.2f} | {result['lightning_count']:>8d} | "
                      f"{result['stop_loss_count']:>10d} | {result['total_trades']:>8d}")
        
        print()        
        # Сравнение 30 vs 90 дней на часовых данных
        print("СРАВНЕНИЕ 30 vs 90 ДНЕЙ (ЧАСОВЫЕ ДАННЫЕ):")
        print("="*80)
        
        # Получаем часовые данные за 30 дней для сравнения
        df_hourly_30 = collector.get_historical_data("ICXUSDT", "1h", 30*24)
        
        print("Результаты за 30 дней (часовые данные, реальные комиссии):")
        result_30 = analyzer.estimate_dual_grid_by_candles(
            df_hourly_30,
            grid_range_pct=10.0,
            grid_step_pct=0.5,
            use_real_commissions=True,
            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            stop_loss_strategy="independent"
        )
        print(f"  30 дней (часовые): {result_30['combined_pct']:.2f}%")
        print(f"  Сделок: {result_30['total_trades']}, Молний: {result_30['lightning_count']}")
        
        print("Результаты за 90 дней (часовые данные, реальные комиссии):")
        result_90_hourly = analyzer.estimate_dual_grid_by_candles(
            df_hourly,
            grid_range_pct=10.0,
            grid_step_pct=0.5,
            use_real_commissions=True,            stop_loss_pct=5.0,
            stop_loss_coverage=0.5,
            stop_loss_strategy="independent"
        )
        print(f"  90 дней (часовые): {result_90_hourly['combined_pct']:.2f}%")
        print(f"  Сделок: {result_90_hourly['total_trades']}, Молний: {result_90_hourly['lightning_count']}")
        
        # Пересчет в месячную доходность
        monthly_30 = result_30['combined_pct']
        monthly_90 = result_90_hourly['combined_pct'] / 3  # 90 дней = 3 месяца
        
        print(f"\nПересчет в месячную доходность:")
        print(f"  30 дней (1 месяц): {monthly_30:.2f}%")
        print(f"  90 дней (в месяц): {monthly_90:.2f}%")
        print(f"  Разница: {monthly_30 - monthly_90:.2f}%")
        
        if abs(monthly_30 - monthly_90) > 10:
            print("⚠️  Значительная разница в результатах!")
        else:
            print("✅ Результаты сопоставимы")        
        # Анализ лучших результатов за 90 дней
        print(f"\nЛУЧШИЕ РЕЗУЛЬТАТЫ ЗА 90 ДНЕЙ (ЧАСОВЫЕ ДАННЫЕ):")
        best_90 = max(results_90, key=lambda x: x['simulation_pnl'])
        print(f"Лучший результат: {best_90['simulation_pnl']:.2f}% "
              f"(диапазон {best_90['grid_range']}%, стоп-лосс {best_90['stop_loss']}%)")
        print(f"В месячном эквиваленте: {best_90['simulation_pnl'] / 3:.2f}%")
        print(f"Сделок: {best_90['total_trades']} (Maker: {best_90['maker_trades']}, Taker: {best_90['taker_trades']})")
        
        # Дополнительная статистика
        print(f"\nДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:")
        print("="*50)
        avg_pnl = sum([r['simulation_pnl'] for r in results_90]) / len(results_90)
        avg_trades = sum([r['total_trades'] for r in results_90]) / len(results_90)
        print(f"Средняя доходность по всем тестам: {avg_pnl:.2f}%")
        print(f"Среднее количество сделок: {avg_trades:.0f}")
        print(f"Использованы реальные комиссии Binance: Maker 0.02%, Taker 0.05%")
        print(f"Тестирование на часовых данных для максимальной точности")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_icxusdt_90_days()
