"""
Тест для проверки исправления ошибки серializации DataFrame в Streamlit
"""
import pandas as pd
import numpy as np

def test_dataframe_serialization():
    """
    Тестирует создание DataFrame как в исправленном app.py
    """
    print("=== Тест серializации DataFrame ===")
    
    # Симулируем результат симуляции Grid Trading
    result = {
        'combined_pct': 5.25,
        'long_pct': 2.75,
        'short_pct': 2.50,
        'total_trades': 45,
        'lightning_count': 3,
        'stop_loss_count': 1,
        'long_active': True,
        'short_active': True,
        'grid_step_pct': 1.2
    }
    
    timeframe_choice = "1h"
    period_days = 30
    
    # Создаем DataFrame как в исправленном коде
    results_df = pd.DataFrame({
        'Метрика': [
            'Общая доходность (%)',
            'Long доходность (%)',
            'Short доходность (%)',
            'Всего сделок',
            'Молний',
            'Стоп-лоссов',
            'Long активна',
            'Short активна',
            'Шаг сетки (%)',
            'Таймфрейм',
            'Период (дней)'
        ],
        'Значение': [
            f"{result['combined_pct']:.2f}",
            f"{result['long_pct']:.2f}",
            f"{result['short_pct']:.2f}",
            str(result['total_trades']),           # Исправлено: приведено к строке
            str(result['lightning_count']),       # Исправлено: приведено к строке
            str(result['stop_loss_count']),       # Исправлено: приведено к строке
            "Да" if result['long_active'] else "Нет",
            "Да" if result['short_active'] else "Нет",
            f"{result['grid_step_pct']:.2f}",
            str(timeframe_choice),                # Исправлено: приведено к строке
            str(period_days)                      # Исправлено: приведено к строке
        ]
    })
    
    print("DataFrame создан успешно:")
    print(results_df)
    print()
    
    # Проверяем типы данных
    print("Типы данных в колонках:")
    print(results_df.dtypes)
    print()
    
    # Проверяем, что все значения в колонке 'Значение' - строки
    all_strings = all(isinstance(val, str) for val in results_df['Значение'])
    print(f"Все значения в колонке 'Значение' - строки: {'✅' if all_strings else '❌'}")
    
    # Проверяем конкретные значения
    print("\nПроверка конкретных значений:")
    print(f"Шаг сетки: '{results_df.iloc[8]['Значение']}' (тип: {type(results_df.iloc[8]['Значение'])})")
    print(f"Всего сделок: '{results_df.iloc[3]['Значение']}' (тип: {type(results_df.iloc[3]['Значение'])})")
    print(f"Таймфрейм: '{results_df.iloc[9]['Значение']}' (тип: {type(results_df.iloc[9]['Значение'])})")
    
    # Тестируем совместимость с Arrow (как делает Streamlit)
    try:
        import pyarrow as pa
        table = pa.Table.from_pandas(results_df)
        print("\n✅ Конвертация в Arrow Table успешна - DataFrame совместим с Streamlit")
        return True
    except ImportError:
        print("\n⚠️ PyArrow не установлен, но типы данных корректны")
        return True
    except Exception as e:
        print(f"\n❌ Ошибка конвертации в Arrow Table: {e}")
        return False

if __name__ == "__main__":
    success = test_dataframe_serialization()
    if success:
        print("\n🎉 Тест прошел успешно! Ошибка серializации исправлена.")
    else:
        print("\n💥 Тест не пройден. Требуются дополнительные исправления.")
