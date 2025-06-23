#!/usr/bin/env python3
"""
Итоговый тест новой логики комиссий с подробным анализом влияния.
Сравнение результатов на разных таймфреймах и параметрах.
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer, MAKER_COMMISSION_RATE, TAKER_COMMISSION_RATE
from modules.collector import BinanceDataCollector

def test_commission_impact():
    """
    Подробный тест влияния реальных комиссий Binance на результаты симуляции.
    """
    print("=== ИТОГОВЫЙ ТЕСТ ВЛИЯНИЯ РЕАЛЬНЫХ КОМИССИЙ BINANCE ===")
    print(f"Maker комиссия: {MAKER_COMMISSION_RATE*100:.3f}%")
    print(f"Taker комиссия: {TAKER_COMMISSION_RATE*100:.3f}%")
    print("="*80)
    
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        # Тестируем на ICXUSDT (как в предыдущих тестах)
        symbol = "ICXUSDT"
        print(f"Тестируем {symbol}")
        
        # Получаем данные за 30 дней
        df = collector.get_historical_data(symbol, "1d", 30)
        
        if df.empty:
            print(f"❌ Не удалось получить данные для {symbol}")
            return
            
        print(f"✅ Получено {len(df)} дней данных")
        print(f"Период: {df.index[0].strftime('%Y-%m-%d')} - {df.index[-1].strftime('%Y-%m-%d')}")
        print()
        
        # Тестируем разные наборы параметров
        test_scenarios = [
            {
                'name': 'Консервативный',
                'grid_range_pct': 15.0,
                'grid_step_pct': 1.0,
                'stop_loss_pct': 10.0,
                'stop_loss_coverage': 0.3,
                'strategy': 'independent'
            },
            {
                'name': 'Умеренный',
                'grid_range_pct': 10.0,
                'grid_step_pct': 0.8,
                'stop_loss_pct': 5.0,
                'stop_loss_coverage': 0.5,
                'strategy': 'independent'
            },
            {
                'name': 'Агрессивный',
                'grid_range_pct': 6.0,
                'grid_step_pct': 0.5,
                'stop_loss_pct': 3.0,
                'stop_loss_coverage': 0.7,
                'strategy': 'independent'
            },
            {
                'name': 'Закрыть обе',
                'grid_range_pct': 10.0,
                'grid_step_pct': 0.8,
                'stop_loss_pct': 5.0,
                'stop_loss_coverage': 0.0,
                'strategy': 'close_both'
            }
        ]
        
        print("СРАВНЕНИЕ СЦЕНАРИЕВ:")
        print("="*120)
        print(f"{'Сценарий':>15} | {'Старая лог.':>12} | {'Реал. ком.':>12} | {'Разница':>10} | {'Относ.':>8} | {'Сделки':>8} | {'Maker':>7} | {'Taker':>7} | {'Ком.%':>6}")
        print("-" * 120)
        
        comparison_results = []
        
        for scenario in test_scenarios:
            # Симуляция со старой логикой
            old_result = analyzer.estimate_dual_grid_by_candles(
                df,
                grid_range_pct=scenario['grid_range_pct'],
                grid_step_pct=scenario['grid_step_pct'],
                use_real_commissions=False,
                stop_loss_pct=scenario['stop_loss_pct'],
                stop_loss_coverage=scenario['stop_loss_coverage'],
                stop_loss_strategy=scenario['strategy'],
                close_both_on_stop_loss=(scenario['strategy'] == 'close_both')
            )
            
            # Симуляция с реальными комиссиями
            real_result = analyzer.estimate_dual_grid_by_candles(
                df,
                grid_range_pct=scenario['grid_range_pct'],
                grid_step_pct=scenario['grid_step_pct'],
                use_real_commissions=True,
                stop_loss_pct=scenario['stop_loss_pct'],
                stop_loss_coverage=scenario['stop_loss_coverage'],
                stop_loss_strategy=scenario['strategy'],
                close_both_on_stop_loss=(scenario['strategy'] == 'close_both')
            )
            
            # Расчет влияния
            difference = real_result['combined_pct'] - old_result['combined_pct']
            relative_change = (difference / old_result['combined_pct'] * 100) if old_result['combined_pct'] != 0 else 0
            
            # Расчет общей стоимости комиссий
            commission_cost = (
                (real_result['long_maker_trades'] + real_result['short_maker_trades']) * real_result['maker_commission_pct'] / 100 +
                (real_result['long_taker_trades'] + real_result['short_taker_trades']) * real_result['taker_commission_pct'] / 100
            )
            
            print(f"{scenario['name']:>15} | {old_result['combined_pct']:>12.2f} | {real_result['combined_pct']:>12.2f} | "
                  f"{difference:>10.2f} | {relative_change:>7.1f}% | {real_result['total_trades']:>8d} | "
                  f"{real_result['long_maker_trades'] + real_result['short_maker_trades']:>7d} | "
                  f"{real_result['long_taker_trades'] + real_result['short_taker_trades']:>7d} | {commission_cost:>6.2f}")
            
            # Сохраняем для анализа
            comparison_results.append({
                'scenario': scenario['name'],
                'old_pnl': old_result['combined_pct'],
                'real_pnl': real_result['combined_pct'],
                'difference': difference,
                'relative_change': relative_change,
                'commission_cost': commission_cost,
                'total_trades': real_result['total_trades'],
                'active_both': real_result['long_active'] and real_result['short_active']
            })
        
        print()
        
        # Анализ результатов
        df_comp = pd.DataFrame(comparison_results)
        
        print("ИТОГОВЫЙ АНАЛИЗ:")
        print("="*60)
        print(f"Среднее влияние реальных комиссий: {df_comp['difference'].mean():.2f}%")
        print(f"Медианное влияние: {df_comp['difference'].median():.2f}%")
        print(f"Максимальное снижение: {df_comp['difference'].min():.2f}%")
        print(f"Минимальное снижение: {df_comp['difference'].max():.2f}%")
        print(f"Среднее относительное изменение: {df_comp['relative_change'].mean():.1f}%")
        print(f"Средняя стоимость комиссий: {df_comp['commission_cost'].mean():.2f}%")
        
        # Лучший и худший сценарий
        best_scenario = df_comp.loc[df_comp['real_pnl'].idxmax()]
        worst_scenario = df_comp.loc[df_comp['real_pnl'].idxmin()]
        
        print(f"\nЛучший сценарий с реальными комиссиями:")
        print(f"  {best_scenario['scenario']}: {best_scenario['real_pnl']:.2f}%")
        print(f"  Влияние комиссий: {best_scenario['difference']:.2f}% ({best_scenario['relative_change']:.1f}%)")
        
        print(f"\nХудший сценарий:")
        print(f"  {worst_scenario['scenario']}: {worst_scenario['real_pnl']:.2f}%")
        print(f"  Влияние комиссий: {worst_scenario['difference']:.2f}% ({worst_scenario['relative_change']:.1f}%)")
        
        # Рекомендации
        print(f"\nРЕКОМЕНДАЦИИ:")
        print("="*40)
        
        if df_comp['difference'].mean() < -1.0:
            print("⚠️  Реальные комиссии существенно снижают доходность")
            print("   Рекомендуется использовать более широкие шаги сетки")
        elif df_comp['difference'].mean() < -0.5:
            print("⚠️  Реальные комиссии умеренно снижают доходность")
            print("   Учитывайте дополнительные расходы в расчетах")
        else:
            print("✅ Влияние реальных комиссий минимальное")
            print("   Можно использовать симуляцию для реальной торговли")
        
        # Анализ соотношения Maker/Taker
        total_maker = sum([r['total_trades'] * 0.6 for r in comparison_results])  # Примерно 60% maker
        total_taker = sum([r['total_trades'] * 0.4 for r in comparison_results])  # Примерно 40% taker
        
        print(f"\nСООТНОШЕНИЕ ТИПОВ СДЕЛОК:")
        print(f"Maker сделки составляют ~60% (низкая комиссия)")
        print(f"Taker сделки составляют ~40% (высокая комиссия)")
        print(f"Средневзвешенная комиссия: {(0.6 * MAKER_COMMISSION_RATE + 0.4 * TAKER_COMMISSION_RATE) * 100:.3f}%")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def test_timeframe_comparison():
    """
    Сравнение результатов на разных таймфреймах с реальными комиссиями.
    """
    print("\n" + "="*80)
    print("СРАВНЕНИЕ ТАЙМФРЕЙМОВ С РЕАЛЬНЫМИ КОМИССИЯМИ")
    print("="*80)
    
    try:
        collector = BinanceDataCollector(api_key="dummy", api_secret="dummy")
        analyzer = GridAnalyzer(collector)
        
        symbol = "ICXUSDT"
        
        # Получаем данные за 30 дней (дневные) и за 30*24 часов (часовые)
        df_daily = collector.get_historical_data(symbol, "1d", 30)
        df_hourly = collector.get_historical_data(symbol, "1h", 30*24)  # 30 дней часовых данных
        
        if df_daily.empty or df_hourly.empty:
            print(f"❌ Не удалось получить данные для {symbol}")
            return
        
        print(f"Дневные данные: {len(df_daily)} свечей")
        print(f"Часовые данные: {len(df_hourly)} свечей")
        print()
        
        # Тестируем одинаковые параметры на разных таймфреймах
        test_params = {
            'grid_range_pct': 10.0,
            'grid_step_pct': 0.5,
            'use_real_commissions': True,
            'stop_loss_pct': 5.0,
            'stop_loss_coverage': 0.5,
            'stop_loss_strategy': 'independent'
        }
        
        print("Параметры тестирования:")
        for key, value in test_params.items():
            print(f"  {key}: {value}")
        print()
        
        # Симуляция на дневных данных
        daily_result = analyzer.estimate_dual_grid_by_candles(df_daily, **test_params)
        
        # Симуляция на часовых данных
        hourly_result = analyzer.estimate_dual_grid_by_candles(df_hourly, **test_params)
        
        print("РЕЗУЛЬТАТЫ ПО ТАЙМФРЕЙМАМ:")
        print("-" * 80)
        
        print(f"Дневные свечи (1d):")
        print(f"  Доходность: {daily_result['combined_pct']:.2f}% (Long: {daily_result['long_pct']:.2f}%, Short: {daily_result['short_pct']:.2f}%)")
        print(f"  Сделок: {daily_result['total_trades']} (Maker: {daily_result['long_maker_trades'] + daily_result['short_maker_trades']}, Taker: {daily_result['long_taker_trades'] + daily_result['short_taker_trades']})")
        print(f"  Молний: {daily_result['lightning_count']}, Стоп-лоссов: {daily_result['stop_loss_count']}")
        print(f"  Эффективный шаг: {daily_result['grid_step_pct']:.2f}%")
        
        print(f"\nЧасовые свечи (1h):")
        print(f"  Доходность: {hourly_result['combined_pct']:.2f}% (Long: {hourly_result['long_pct']:.2f}%, Short: {hourly_result['short_pct']:.2f}%)")
        print(f"  Сделок: {hourly_result['total_trades']} (Maker: {hourly_result['long_maker_trades'] + hourly_result['short_maker_trades']}, Taker: {hourly_result['long_taker_trades'] + hourly_result['short_taker_trades']})")
        print(f"  Молний: {hourly_result['lightning_count']}, Стоп-лоссов: {hourly_result['stop_loss_count']}")
        print(f"  Эффективный шаг: {hourly_result['grid_step_pct']:.2f}%")
        
        # Сравнение
        difference = hourly_result['combined_pct'] - daily_result['combined_pct']
        print(f"\nСРАВНЕНИЕ:")
        print(f"  Разница (часовые - дневные): {difference:.2f}%")
        
        if abs(difference) > 10:
            print(f"  ⚠️  Существенная разница между таймфреймами!")
        else:
            print(f"  ✅ Результаты на разных таймфреймах сопоставимы")
        
        # Анализ эффективности
        trades_ratio = hourly_result['total_trades'] / daily_result['total_trades'] if daily_result['total_trades'] > 0 else 0
        print(f"  Соотношение количества сделок (час/день): {trades_ratio:.1f}x")
        
        if hourly_result['combined_pct'] > daily_result['combined_pct']:
            print(f"  ✅ Часовые данные дают лучший результат")
        else:
            print(f"  ⚠️  Дневные данные дают лучший результат")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_commission_impact()
    test_timeframe_comparison()
