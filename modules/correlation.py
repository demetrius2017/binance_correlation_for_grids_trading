"""
Модуль для анализа корреляций между торговыми парами.
Отвечает за расчет матрицы корреляций и визуализацию результатов.
"""

import os
from typing import List, Dict, Any, Optional, Tuple, Union

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from binance.client import Client
from matplotlib.figure import Figure

from .collector import BinanceDataCollector


class CorrelationAnalyzer:
    """
    Класс для анализа корреляций между торговыми парами.
    """
    
    def __init__(self, collector: BinanceDataCollector):
        """
        Инициализация анализатора корреляций.
        
        Args:
            collector: Экземпляр класса BinanceDataCollector для сбора данных
        """
        self.collector = collector
        self.price_data = pd.DataFrame()
        self.correlation_matrix = pd.DataFrame()
        
    def collect_price_data(self, symbols: List[str], days: int = 365) -> pd.DataFrame:
        """
        Сбор данных о ценах для указанных пар.
        
        Args:
            symbols: Список символов торговых пар
            days: Количество дней для анализа
            
        Returns:
            DataFrame с данными о ценах закрытия для всех пар
        """
        all_data = pd.DataFrame()
        
        for symbol in symbols:
            try:
                # Получаем исторические данные
                df = self.collector.get_historical_data(
                    symbol, 
                    Client.KLINE_INTERVAL_1DAY,
                    days
                )
                
                if not df.empty:
                    # Добавляем только цены закрытия
                    if all_data.empty:
                        all_data = pd.DataFrame(index=df.index)
                    
                    all_data[symbol] = df['close']
            except Exception as e:
                print(f"Ошибка при получении данных для {symbol}: {e}")
                continue
        
        # Обрабатываем пропущенные значения (используем ffill вместо устаревшего метода)
        all_data = all_data.ffill()
        
        self.price_data = all_data
        return all_data
    
    def get_price_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Получение данных о ценах для указанной пары.
        
        Args:
            symbol: Символ торговой пары
            
        Returns:
            DataFrame с данными цен или None, если данные недоступны
        """
        # Проверяем, есть ли данные для этой пары
        if self.price_data.empty or symbol not in self.price_data.columns:
            try:
                # Получаем исторические данные, если они еще не были загружены
                df = self.collector.get_historical_data(
                    symbol, Client.KLINE_INTERVAL_1DAY, days=365
                )
                if df.empty:
                    return None
                return df
            except Exception as e:
                print(f"Ошибка при получении данных для пары {symbol}: {e}")
                return None
        else:
            # Извлекаем данные из имеющегося DataFrame и преобразуем их в формат OHLC
            price_series = self.price_data[symbol]
            return pd.DataFrame({
                'close': price_series
            })
    
    def calculate_correlation(self, method: str = 'pearson') -> pd.DataFrame:
        """
        Расчет матрицы корреляций между парами.
        
        Args:
            method: Метод расчета корреляции ('pearson', 'spearman', 'kendall')
            
        Returns:
            Матрица корреляций
        """
        if self.price_data.empty:
            raise ValueError("Нет данных о ценах. Сначала выполните collect_price_data()")
        
        # Рассчитываем корреляцию по логарифмическим доходностям
        returns = np.log(self.price_data / self.price_data.shift(1)).dropna()
        correlation = returns.corr(method=method)
        
        self.correlation_matrix = correlation
        return correlation
    
    def plot_correlation_heatmap(self, figsize: Tuple[int, int] = (12, 10), 
                               cmap: str = 'coolwarm') -> Figure:
        """
        Визуализация матрицы корреляций в виде тепловой карты.
        
        Args:
            figsize: Размер фигуры
            cmap: Цветовая палитра для тепловой карты
            
        Returns:
            Объект Figure с тепловой картой
        """
        if self.correlation_matrix.empty:
            raise ValueError("Нет матрицы корреляций. Сначала выполните calculate_correlation()")
        
        fig = plt.figure(figsize=figsize)
        mask = np.triu(np.ones_like(self.correlation_matrix, dtype=bool))
        
        # Создаем тепловую карту
        sns.heatmap(
            self.correlation_matrix, 
            mask=mask,
            cmap=cmap,
            vmax=1, 
            vmin=-1,
            center=0,
            annot=True,
            fmt=".2f",
            square=True, 
            linewidths=0.5
        )
        
        plt.title('Матрица корреляций')
        return fig
    
    def find_least_correlated_pairs(self, threshold: float = 0.3, 
                                   min_pairs: int = 5) -> List[str]:
        """
        Поиск наименее коррелированных пар.
        
        Args:
            threshold: Пороговое значение корреляции
            min_pairs: Минимальное количество пар для выбора
            
        Returns:
            Список наименее коррелированных пар
        """
        if self.correlation_matrix.empty:
            raise ValueError("Нет матрицы корреляций. Сначала выполните calculate_correlation()")
        
        # Начинаем с пары с наименьшей средней корреляцией
        mean_corr = self.correlation_matrix.abs().mean().sort_values()
        selected_pairs = [mean_corr.index[0]]
        
        # Добавляем пары, имеющие корреляцию ниже порога с уже выбранными
        remaining_pairs = list(mean_corr.index[1:])
        
        while len(selected_pairs) < min_pairs and remaining_pairs:
            best_pair = None
            min_max_corr = float('inf')
            
            for pair in remaining_pairs:
                # Максимальная корреляция с уже выбранными парами
                correlations = []
                for selected in selected_pairs:
                    # Получаем значение корреляции между текущей парой и уже выбранной
                    corr_value = float(self.correlation_matrix.loc[pair, selected])
                    correlations.append(abs(corr_value))
                
                if correlations:
                    max_corr = max(correlations)
                    
                    if max_corr < min_max_corr:
                        min_max_corr = max_corr
                        best_pair = pair
            
            if best_pair and min_max_corr <= threshold:
                selected_pairs.append(best_pair)
                remaining_pairs.remove(best_pair)
            else:
                # Если не можем найти пару с корреляцией ниже порога, увеличиваем порог
                threshold += 0.05
                if threshold > 0.7:  # Предельное значение порога
                    break
        
        return selected_pairs
    
    def export_correlation_matrix(self, filepath: str = "correlation_matrix.csv") -> None:
        """
        Экспорт матрицы корреляций в CSV-файл.
        
        Args:
            filepath: Путь к файлу для сохранения
        """
        if self.correlation_matrix.empty:
            raise ValueError("Нет матрицы корреляций. Сначала выполните calculate_correlation()")
        
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        # Сохраняем матрицу корреляций
        self.correlation_matrix.to_csv(filepath)
        print(f"Матрица корреляций сохранена в {filepath}")
