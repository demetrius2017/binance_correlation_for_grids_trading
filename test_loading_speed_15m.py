"""
Тест скорости загрузки данных Grid Trading

Проверяем скорость загрузки разных объемов данных:
- 1d за 30 дней = 30 свечей
- 1d за 90 дней = 90 свечей  
- 1h за 30 дней = 720 свечей
- 1h за 90 дней = 2160 свечей
- 15m за 10 дней = 960 свечей
- 15m за 30 дней = 2880 свечей (ограничение API: 1000 свечей)
"""

import time
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.collector import BinanceDataCollector

def test_loading_speed():
    """Тестирование скорости загрузки данных"""
    
    # Инициализация (без реальных ключей будет использовать публичные endpoints)
    collector = BinanceDataCollector("", "")
    
    test_symbol = "BTCUSDT"  # Популярная пара
    
    tests = [
        ("1d", 30, "30 дней дневных свечей"),
        ("1d", 90, "90 дней дневных свечей"),
        ("1h", 30, "30 дней часовых свечей (720 свечей)"),
        ("1h", 90, "90 дней часовых свечей (2160 свечей)"),
        ("15m", 10, "10 дней 15-минутных свечей (960 свечей)"),
        ("15m", 30, "30 дней 15-минутных свечей (макс. 1000 свечей)")
    ]
    
    print(f"🔍 Тестирование скорости загрузки данных для {test_symbol}")
    print("=" * 60)
    
    for interval, days, description in tests:
        print(f"\n📊 {description}")
        print(f"   Параметры: interval={interval}, days={days}")
        
        start_time = time.time()
        try:
            if interval == "15m":
                # Для 15-минутных данных
                df = collector.get_historical_data(test_symbol, interval, days * 24 * 4)
            elif interval == "1h":
                # Для часовых данных
                df = collector.get_historical_data(test_symbol, interval, days * 24)
            else:
                df = collector.get_historical_data(test_symbol, interval, days)
            
            end_time = time.time()
            loading_time = end_time - start_time
            
            if not df.empty:
                print(f"   ✅ Загружено: {len(df)} свечей")
                print(f"   ⏱️  Время загрузки: {loading_time:.2f} секунд")
                print(f"   🚀 Скорость: {len(df)/loading_time:.0f} свечей/сек")
                
                # Анализ скорости
                if loading_time < 2:
                    speed_rating = "🟢 Быстро"
                elif loading_time < 5:
                    speed_rating = "🟡 Нормально"
                else:
                    speed_rating = "🔴 Медленно"
                    
                print(f"   📈 Оценка: {speed_rating}")
            else:
                print(f"   ❌ Ошибка: данные не загружены")
                
        except Exception as e:
            end_time = time.time()
            loading_time = end_time - start_time
            print(f"   ❌ Ошибка загрузки: {str(e)}")
            print(f"   ⏱️  Время до ошибки: {loading_time:.2f} секунд")
    
    print("\n" + "=" * 60)
    print("🎯 РЕКОМЕНДАЦИИ:")
    print("• Для быстрого тестирования: используйте дневные данные (1d)")
    print("• Для высокой точности: 15m данные, но API ограничен 1000 свечами (~10 дней)")
    print("• Для баланса точности и объема: 1h за 30-90 дней = точные результаты за разумное время")

if __name__ == "__main__":
    test_loading_speed()
