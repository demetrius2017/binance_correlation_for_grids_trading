"""
Модуль для формирования оптимального портфеля из отобранных торговых пар.
"""

import os
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from binance.client import Client

from .collector import BinanceDataCollector
from .correlation import CorrelationAnalyzer


class PortfolioBuilder:
    """
    Класс для построения оптимального портфеля из торговых пар.
    """
    
    def __init__(self, collector: BinanceDataCollector, correlation_analyzer: CorrelationAnalyzer):
        """
        Инициализация построителя портфеля.
        
        Args:
            collector: Экземпляр класса BinanceDataCollector для сбора данных
            correlation_analyzer: Экземпляр класса CorrelationAnalyzer для анализа корреляций
        """
        self.collector = collector
        self.correlation_analyzer = correlation_analyzer
        self.portfolio_symbols = []
        self.optimal_weights = None
        self.portfolio_stats = {}
        
    def set_portfolio_symbols(self, symbols: List[str]) -> None:
        """
        Установка списка символов для формирования портфеля.
        
        Args:
            symbols: Список символов торговых пар
        """
        self.portfolio_symbols = symbols
        
    def _calculate_portfolio_performance(self, weights: np.ndarray, returns: pd.DataFrame) -> Tuple[float, float]:
        """
        Расчет доходности и риска портфеля.
        
        Args:
            weights: Веса активов в портфеле
            returns: DataFrame с доходностями активов
            
        Returns:
            Кортеж (доходность, риск)
        """
        # Проверяем и корректируем размерности
        if len(weights) != len(returns.columns):
            print(f"ВНИМАНИЕ: Размерности не совпадают: веса {len(weights)}, доходности {len(returns.columns)}")
            # Обрезаем веса, если их больше чем столбцов в returns
            if len(weights) > len(returns.columns):
                weights = weights[:len(returns.columns)]
            # Или обрезаем returns, если столбцов больше чем весов
            else:
                returns = returns.iloc[:, :len(weights)]
            print(f"Скорректированные размерности: веса {len(weights)}, доходности {len(returns.columns)}")
            
        # Рассчитываем ожидаемую доходность портфеля
        portfolio_return = np.sum(returns.mean() * weights) * 252  # Годовая доходность
        
        # Рассчитываем риск (волатильность) портфеля
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        
        return portfolio_return, portfolio_volatility
    
    def _objective_sharpe(self, weights: np.ndarray, returns: pd.DataFrame, risk_free_rate: float = 0.0) -> float:
        """
        Функция для оптимизации коэффициента Шарпа.
        
        Args:
            weights: Веса активов в портфеле
            returns: DataFrame с доходностями активов
            risk_free_rate: Безрисковая ставка
            
        Returns:
            Отрицательное значение коэффициента Шарпа
        """
        portfolio_return, portfolio_volatility = self._calculate_portfolio_performance(weights, returns)
        
        # Рассчитываем коэффициент Шарпа
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
        
        # Возвращаем отрицательное значение, так как мы минимизируем
        return -sharpe_ratio
    
    def _minimize_volatility(self, weights: np.ndarray, returns: pd.DataFrame) -> float:
        """
        Функция для минимизации волатильности портфеля.
        
        Args:
            weights: Веса активов в портфеле
            returns: DataFrame с доходностями активов
            
        Returns:
            Волатильность портфеля
        """
        _, portfolio_volatility = self._calculate_portfolio_performance(weights, returns)
        return portfolio_volatility
    
    def build_optimal_portfolio(self, optimization_goal: str = 'sharpe', 
                              risk_free_rate: float = 0.0) -> Dict[str, Any]:
        """
        Построение оптимального портфеля из выбранных пар.
        
        Args:
            optimization_goal: Цель оптимизации ('sharpe', 'min_volatility')
            risk_free_rate: Безрисковая ставка для расчета коэффициента Шарпа
            
        Returns:
            Словарь со статистикой оптимального портфеля
        """
        if not self.portfolio_symbols:
            raise ValueError("Список символов для портфеля пуст. Используйте set_portfolio_symbols()")
        
        # Собираем данные о ценах, если они еще не собраны
        if self.correlation_analyzer.price_data.empty:
            self.correlation_analyzer.collect_price_data(self.portfolio_symbols)
        
        # Получаем данные о ценах и рассчитываем доходности
        price_data = self.correlation_analyzer.price_data
        
        if price_data.empty:
            raise ValueError("Не удалось получить данные о ценах")
        
        # Проверяем, что у нас есть данные для всех указанных символов
        available_symbols = [sym for sym in self.portfolio_symbols if sym in price_data.columns]
        if len(available_symbols) < len(self.portfolio_symbols):
            missing = set(self.portfolio_symbols) - set(available_symbols)
            print(f"ВНИМАНИЕ: Отсутствуют данные для следующих символов: {missing}")
            self.portfolio_symbols = available_symbols
        
        if len(self.portfolio_symbols) < 2:
            raise ValueError("Необходимо минимум 2 символа для формирования портфеля")
        
        # Используем только доступные символы
        price_data = price_data[self.portfolio_symbols]
        
        # Рассчитываем логарифмические доходности
        returns = np.log(price_data / price_data.shift(1)).dropna()
        
        # Количество активов
        num_assets = len(self.portfolio_symbols)
        
        # Начальные веса (равные)
        initial_weights = np.array([1.0 / num_assets] * num_assets)
        
        # Ограничения: сумма весов = 1
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        # Границы: все веса между 0 и 1
        bounds = tuple((0, 1) for _ in range(num_assets))
        
        if optimization_goal == 'sharpe':
            # Оптимизация по коэффициенту Шарпа
            result = minimize(
                self._objective_sharpe,
                initial_weights,
                args=(returns, risk_free_rate),
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
        else:
            # Оптимизация по минимальной волатильности
            result = minimize(
                self._minimize_volatility,
                initial_weights,
                args=(returns,),
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
        
        # Получаем оптимальные веса
        optimal_weights = result['x']
        self.optimal_weights = optimal_weights
        
        # Рассчитываем доходность и риск оптимального портфеля
        portfolio_return, portfolio_volatility = self._calculate_portfolio_performance(
            optimal_weights, returns
        )
        
        # Рассчитываем коэффициент Шарпа
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
        
        # Создаем словарь с результатами
        portfolio_stats = {
            'symbols': self.portfolio_symbols,
            'weights': optimal_weights,
            'expected_return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio
        }
        
        self.portfolio_stats = portfolio_stats
        return portfolio_stats
    
    def plot_portfolio_allocation(self, figsize: Tuple[int, int] = (12, 8)) -> plt.Figure:
        """
        Визуализация распределения активов в портфеле.
        
        Args:
            figsize: Размер фигуры
            
        Returns:
            Объект Figure с диаграммой распределения
        """
        if not self.optimal_weights:
            raise ValueError("Оптимальные веса не рассчитаны. Сначала выполните build_optimal_portfolio()")
        
        # Создаем DataFrame с весами
        weights_df = pd.DataFrame({
            'Symbol': self.portfolio_symbols,
            'Weight': self.optimal_weights
        })
        
        # Сортируем по весу (от большего к меньшему)
        weights_df = weights_df.sort_values('Weight', ascending=False)
        
        # Создаем диаграмму
        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(weights_df['Symbol'], weights_df['Weight'], color='skyblue')
        
        # Добавляем метки
        ax.set_title('Распределение активов в оптимальном портфеле', fontsize=16)
        ax.set_xlabel('Торговая пара', fontsize=14)
        ax.set_ylabel('Вес в портфеле', fontsize=14)
        ax.set_ylim(0, max(weights_df['Weight']) * 1.2)
        
        # Добавляем значения на столбцы
        for i, v in enumerate(weights_df['Weight']):
            ax.text(i, v + 0.01, f'{v:.2%}', ha='center', fontsize=12)
        
        plt.tight_layout()
        return fig
    
    def save_portfolio_results(self, filename: str = "optimal_portfolio.csv") -> None:
        """
        Сохранение результатов оптимизации портфеля в CSV-файл.
        
        Args:
            filename: Имя файла для сохранения
        """
        if not self.portfolio_stats:
            raise ValueError("Статистика портфеля не рассчитана. Сначала выполните build_optimal_portfolio()")
        
        # Создаем DataFrame с весами
        weights_df = pd.DataFrame({
            'Symbol': self.portfolio_symbols,
            'Weight': self.optimal_weights
        })
        
        # Создаем директорию для данных, если она не существует
        os.makedirs("data/processed", exist_ok=True)
        
        # Сохраняем результаты
        filepath = os.path.join("data/processed", filename)
        weights_df.to_csv(filepath, index=False)
        
        # Сохраняем общую статистику в отдельный файл
        stats_filepath = os.path.join("data/processed", "portfolio_stats.csv")
        stats_df = pd.DataFrame({
            'Metric': ['Return', 'Volatility', 'Sharpe Ratio'],
            'Value': [
                self.portfolio_stats['expected_return'],
                self.portfolio_stats['volatility'],
                self.portfolio_stats['sharpe_ratio']
            ]
        })
        stats_df.to_csv(stats_filepath, index=False)
        
        print(f"Результаты оптимизации портфеля сохранены в {filepath} и {stats_filepath}")
