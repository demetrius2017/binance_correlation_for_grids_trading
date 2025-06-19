"""
Модуль обработки данных для анализа торговых пар Binance.
Отвечает за анализ, ранжирование пар и их отбор по заданным критериям.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from binance.client import Client

from .collector import BinanceDataCollector


class DataProcessor:
    """
    Класс для обработки и анализа данных торговых пар.
    """
    
    def __init__(self, collector: BinanceDataCollector):
        """
        Инициализация процессора данных.
        
        Args:
            collector: Экземпляр класса BinanceDataCollector для сбора данных
        """
        self.collector = collector
        self.pairs_data = {}
        self.ranked_pairs = pd.DataFrame()
        
    def analyze_all_pairs(self, min_age_days: int = 365, min_volatility: float = 5.0, 
                         max_range_percent: float = 30.0) -> pd.DataFrame:
        """
        Анализ всех подходящих торговых пар.
        
        Args:
            min_age_days: Минимальный возраст пары в днях
            min_volatility: Минимальная дневная волатильность в процентах
            max_range_percent: Максимальный диапазон цены в процентах для определения боковика
            
        Returns:
            DataFrame с результатами анализа всех пар
        """
        # Получаем пары старше указанного возраста
        print("Запуск анализа пар...")
        old_pairs = self.collector.get_pairs_older_than_year()
        
        if not old_pairs:
            print("Не найдено пар, соответствующих критерию возраста!")
            return pd.DataFrame()  # Возвращаем пустой DataFrame
        
        print(f"Начинаем анализ {len(old_pairs)} пар...")
        results = []
        
        for i, symbol in enumerate(old_pairs):
            try:
                print(f"Анализ пары {i+1}/{len(old_pairs)}: {symbol}")
                
                # Получаем статистику по паре
                stats = self.collector.get_pair_stats(symbol, days=min_age_days)
                
                if stats and stats['avg_daily_volatility'] >= min_volatility:
                    # Сохраняем данные для дальнейшего анализа
                    self.pairs_data[symbol] = stats
                    results.append(stats)
                    print(f"Пара {symbol} добавлена в результаты (волатильность: {stats['avg_daily_volatility']:.2f}%)")
                else:
                    if stats:
                        print(f"Пара {symbol} не соответствует критерию волатильности ({stats['avg_daily_volatility']:.2f}% < {min_volatility}%)")
                    else:
                        print(f"Не удалось получить статистику для пары {symbol}")
            except Exception as e:
                print(f"Ошибка при анализе пары {symbol}: {str(e)}")
                continue
                
        # Создаем DataFrame из результатов
        df_results = pd.DataFrame(results)
        
        print(f"Анализ завершен. Отобрано {len(df_results)} пар, соответствующих критериям")
        return df_results
    
    def rank_pairs(self, volatility_weight: float = 0.7, 
                  sideways_weight: float = 0.3) -> pd.DataFrame:
        """
        Ранжирование пар на основе заданных критериев.
        
        Args:
            volatility_weight: Вес фактора волатильности в ранжировании
            sideways_weight: Вес фактора нахождения в боковике в ранжировании
            
        Returns:
            DataFrame с ранжированными парами
        """
        if not self.pairs_data:
            raise ValueError("Нет данных для ранжирования. Сначала выполните analyze_all_pairs()")
        
        results = pd.DataFrame(self.pairs_data.values())
        
        # Нормализуем значения для корректного ранжирования
        results['volatility_score'] = results['avg_daily_volatility'] / results['avg_daily_volatility'].max()
        
        # Для боковика: чем меньше диапазон, тем лучше (инвертируем)
        max_range = results['price_range_percent'].max()
        if max_range > 0:
            results['sideways_score'] = 1 - (results['price_range_percent'] / max_range)
        else:
            results['sideways_score'] = 1.0
        
        # Вычисляем итоговый рейтинг
        results['total_score'] = (
            results['volatility_score'] * volatility_weight + 
            results['sideways_score'] * sideways_weight
        )
        
        # Сортируем по итоговому рейтингу
        ranked = results.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        self.ranked_pairs = ranked
        return ranked
    
    def get_top_pairs(self, top_n: int = 10) -> pd.DataFrame:
        """
        Получение топ-N пар из ранжированного списка.
        
        Args:
            top_n: Количество пар для выборки
            
        Returns:
            DataFrame с топ-N парами
        """
        if self.ranked_pairs.empty:
            raise ValueError("Нет ранжированных пар. Сначала выполните rank_pairs()")
        
        return self.ranked_pairs.head(top_n)
    
    def save_results(self, filename: str = "ranked_pairs.csv") -> None:
        """
        Сохранение результатов анализа в CSV-файл.
        
        Args:
            filename: Имя файла для сохранения результатов
        """
        if self.ranked_pairs.empty:
            raise ValueError("Нет ранжированных пар. Сначала выполните rank_pairs()")
        
        # Создаем директорию для данных, если она не существует
        os.makedirs("data/processed", exist_ok=True)
        
        # Сохраняем результаты
        filepath = os.path.join("data/processed", filename)
        self.ranked_pairs.to_csv(filepath, index=False)
        print(f"Результаты сохранены в {filepath}")


if __name__ == "__main__":
    # Пример использования
    api_key = "YOUR_API_KEY"
    api_secret = "YOUR_API_SECRET"
    
    collector = BinanceDataCollector(api_key, api_secret)
    processor = DataProcessor(collector)
    
    # Анализируем пары
    analyzed = processor.analyze_all_pairs(
        min_age_days=365,
        min_volatility=5.0,
        max_range_percent=30.0
    )
    
    print(f"Проанализировано {len(analyzed)} пар")
    
    # Ранжируем пары
    ranked = processor.rank_pairs(
        volatility_weight=0.7,
        sideways_weight=0.3
    )
    
    # Выводим топ-5 пар
    top_pairs = processor.get_top_pairs(5)
    print("\nТоп-5 пар:")
    print(top_pairs[['symbol', 'avg_daily_volatility', 'price_range_percent', 'total_score']])
