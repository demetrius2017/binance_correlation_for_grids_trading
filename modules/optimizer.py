"""
Модуль автоматической оптимизации параметров Grid Trading с использованием генетического алгоритма.
Полная версия для Railway.
"""

import random
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

@dataclass
class OptimizationParams:
    """Параметры для оптимизации"""
    grid_range_pct: float
    grid_step_pct: float
    stop_loss_pct: float
    
    def to_dict(self):
        return {
            'grid_range_pct': self.grid_range_pct,
            'grid_step_pct': self.grid_step_pct,
            'stop_loss_pct': self.stop_loss_pct
        }

@dataclass
class OptimizationResult:
    """Результат оптимизации"""
    params: OptimizationParams
    backtest_score: float
    forward_score: float
    combined_score: float
    trades_count: int
    drawdown: float
    
class GridOptimizer:
    """Класс для оптимизации параметров Grid Trading"""
    
    def __init__(self, grid_analyzer, commission_rate=0.0005):
        self.grid_analyzer = grid_analyzer
        self.commission_rate = commission_rate
        
        # Границы параметров для оптимизации
        self.param_bounds = {
            'grid_range_pct': (5.0, 50.0),    # 5-50%
            'grid_step_pct': (0.1, 5.0),      # 0.1-5%
            'stop_loss_pct': (0.0, 15.0)      # 0-15%
        }
        
    def create_random_params(self) -> OptimizationParams:
        """Создает случайные параметры в заданных границах с кратными шагами"""
        # Диапазон сетки кратно 5% (5, 10, 15, ..., 50)
        grid_range_options = list(range(5, 55, 5))  # [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        grid_range_pct = float(random.choice(grid_range_options))
        
        # Шаг сетки кратно 0.5% (0.5, 1.0, 1.5, ..., 5.0)
        grid_step_options = [round(x * 0.5, 1) for x in range(1, 11)]  # [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
        grid_step_pct = random.choice(grid_step_options)
        
        # Стоп-лосс кратно 5% (0, 5, 10, 15)
        stop_loss_options = [0.0, 5.0, 10.0, 15.0]
        stop_loss_pct = random.choice(stop_loss_options)
        
        return OptimizationParams(
            grid_range_pct=grid_range_pct,
            grid_step_pct=grid_step_pct,
            stop_loss_pct=stop_loss_pct
        )
        
    def mutate_params(self, params: OptimizationParams, mutation_rate=0.1) -> OptimizationParams:
        """Мутация параметров для генетического алгоритма с кратными шагами"""
        new_params = OptimizationParams(
            grid_range_pct=params.grid_range_pct,
            grid_step_pct=params.grid_step_pct,
            stop_loss_pct=params.stop_loss_pct
        )
        
        # Мутация диапазона сетки (кратно 5%)
        if random.random() < mutation_rate:
            grid_range_options = list(range(5, 55, 5))  # [5, 10, 15, ..., 50]
            current_idx = grid_range_options.index(int(params.grid_range_pct)) if int(params.grid_range_pct) in grid_range_options else 0
            # Выбираем соседний элемент
            if current_idx > 0 and current_idx < len(grid_range_options) - 1:
                new_idx = random.choice([current_idx - 1, current_idx + 1])
            elif current_idx == 0:
                new_idx = current_idx + 1
            else:
                new_idx = current_idx - 1
            new_params.grid_range_pct = float(grid_range_options[new_idx])
            
        # Мутация шага сетки (кратно 0.5%)
        if random.random() < mutation_rate:
            grid_step_options = [round(x * 0.5, 1) for x in range(1, 11)]  # [0.5, 1.0, 1.5, ..., 5.0]
            current_idx = grid_step_options.index(params.grid_step_pct) if params.grid_step_pct in grid_step_options else 0
            # Выбираем соседний элемент
            if current_idx > 0 and current_idx < len(grid_step_options) - 1:
                new_idx = random.choice([current_idx - 1, current_idx + 1])
            elif current_idx == 0:
                new_idx = current_idx + 1
            else:
                new_idx = current_idx - 1
            new_params.grid_step_pct = grid_step_options[new_idx]
            
        # Мутация стоп-лосса (кратно 5%)
        if random.random() < mutation_rate:
            stop_loss_options = [0.0, 5.0, 10.0, 15.0]
            current_idx = stop_loss_options.index(params.stop_loss_pct) if params.stop_loss_pct in stop_loss_options else 0
            # Выбираем соседний элемент
            if current_idx > 0 and current_idx < len(stop_loss_options) - 1:
                new_idx = random.choice([current_idx - 1, current_idx + 1])
            elif current_idx == 0:
                new_idx = current_idx + 1
            else:
                new_idx = current_idx - 1
            new_params.stop_loss_pct = stop_loss_options[new_idx]
            
        return new_params
    
    def params_to_key(self, params: OptimizationParams) -> str:
        """Создает уникальный ключ для параметров"""
        return f"{params.grid_range_pct:.1f}_{params.grid_step_pct:.1f}_{params.stop_loss_pct:.1f}"
    
    def remove_duplicate_params(self, params_list: List[OptimizationParams]) -> List[OptimizationParams]:
        """Удаляет дублирующиеся параметры из списка"""
        seen_keys = set()
        unique_params = []
        
        for params in params_list:
            key = self.params_to_key(params)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_params.append(params)
        
        return unique_params
        
    def crossover_params(self, parent1: OptimizationParams, parent2: OptimizationParams) -> OptimizationParams:
        """Скрещивание параметров двух родителей"""
        return OptimizationParams(
            grid_range_pct=random.choice([parent1.grid_range_pct, parent2.grid_range_pct]),
            grid_step_pct=random.choice([parent1.grid_step_pct, parent2.grid_step_pct]),
            stop_loss_pct=random.choice([parent1.stop_loss_pct, parent2.stop_loss_pct])
        )
        
    def evaluate_params(self, params: OptimizationParams, backtest_df: pd.DataFrame, 
                       forward_df: pd.DataFrame, initial_balance: float) -> OptimizationResult:
        """Оценка параметров на бэктесте и форвард тесте"""
        
        try:
            # Бэктест
            stop_loss = params.stop_loss_pct if params.stop_loss_pct > 0 else None
            
            stats_long_bt, stats_short_bt, _, _ = self.grid_analyzer.estimate_dual_grid_by_candles_realistic(
                df=backtest_df,
                initial_balance_long=initial_balance,
                initial_balance_short=initial_balance,
                grid_range_pct=params.grid_range_pct,
                grid_step_pct=params.grid_step_pct,
                order_size_usd_long=0,
                order_size_usd_short=0,
                commission_pct=self.commission_rate * 100,
                stop_loss_pct=stop_loss,
                debug=False
            )
            
            # Форвард тест
            stats_long_ft, stats_short_ft, _, _ = self.grid_analyzer.estimate_dual_grid_by_candles_realistic(
                df=forward_df,
                initial_balance_long=initial_balance,
                initial_balance_short=initial_balance,
                grid_range_pct=params.grid_range_pct,
                grid_step_pct=params.grid_step_pct,
                order_size_usd_long=0,
                order_size_usd_short=0,
                commission_pct=self.commission_rate * 100,
                stop_loss_pct=stop_loss,
                debug=False
            )
            
            # Расчет метрик
            backtest_pnl_pct = ((stats_long_bt['total_pnl'] + stats_short_bt['total_pnl']) / (initial_balance * 2)) * 100
            forward_pnl_pct = ((stats_long_ft['total_pnl'] + stats_short_ft['total_pnl']) / (initial_balance * 2)) * 100
            
            # Считаем стабильность как разность между бэктестом и форвардом
            stability_penalty = abs(backtest_pnl_pct - forward_pnl_pct) * 0.5
            
            # Комбинированный скор: среднее арифметическое минус штраф за нестабильность
            combined_score = (backtest_pnl_pct + forward_pnl_pct) / 2 - stability_penalty
            
            # Общее количество сделок
            total_trades = stats_long_bt['trades_count'] + stats_short_bt['trades_count'] + \
                          stats_long_ft['trades_count'] + stats_short_ft['trades_count']
            
            # Примерный расчет просадки (упрощенный)
            drawdown = max(0, -min(backtest_pnl_pct, forward_pnl_pct))
            
            return OptimizationResult(
                params=params,
                backtest_score=backtest_pnl_pct,
                forward_score=forward_pnl_pct,
                combined_score=combined_score,
                trades_count=total_trades,
                drawdown=drawdown
            )
            
        except Exception as e:
            # В случае ошибки возвращаем плохой результат
            return OptimizationResult(
                params=params,
                backtest_score=-100.0,
                forward_score=-100.0,
                combined_score=-100.0,
                trades_count=0,
                drawdown=100.0
            )
    
    def optimize_genetic(self, df: pd.DataFrame, initial_balance: float, 
                        population_size=50, generations=20, 
                        forward_test_pct=0.3, max_workers=4,
                        progress_callback=None) -> List[OptimizationResult]:
        """
        Генетический алгоритм оптимизации параметров
        
        Args:
            df: Исторические данные DataFrame
            initial_balance: Начальный баланс
            population_size: Размер популяции
            generations: Количество поколений
            forward_test_pct: Процент данных для форвард теста (0.3 = 30%)
            max_workers: Количество потоков
            progress_callback: Функция для отображения прогресса
        """
        
        # Разделение данных на бэктест и форвард тест
        split_idx = int(len(df) * (1 - forward_test_pct))
        backtest_df = df.iloc[:split_idx].copy()
        forward_df = df.iloc[split_idx:].copy()
        
        if progress_callback:
            progress_callback(f"Разделение данных: {len(backtest_df)} точек для бэктеста, {len(forward_df)} для форвард теста")
        
        # Создание начальной популяции без дубликатов
        population_candidates = []
        while len(population_candidates) < population_size * 2:  # Генерируем больше кандидатов
            population_candidates.append(self.create_random_params())
        
        population = self.remove_duplicate_params(population_candidates)[:population_size]
        
        # Если после удаления дубликатов недостаточно особей, добавляем случайные
        while len(population) < population_size:
            population.append(self.create_random_params())
            
        best_results = []
        
        for generation in range(generations):
            if progress_callback:
                progress_callback(f"Поколение {generation + 1}/{generations}")
            
            # Оценка популяции в многопоточном режиме
            generation_results = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_params = {
                    executor.submit(
                        self.evaluate_params, 
                        params, 
                        backtest_df, 
                        forward_df, 
                        initial_balance
                    ): params for params in population
                }
                
                for future in as_completed(future_to_params):
                    result = future.result()
                    generation_results.append(result)
            
            # Сортировка по комбинированному скору
            generation_results.sort(key=lambda x: x.combined_score, reverse=True)
            
            # Сохранение лучшего результата поколения
            best_results.append(generation_results[0])
            
            if progress_callback:
                best = generation_results[0]
                progress_callback(f"Лучший результат поколения: {best.combined_score:.2f}% "
                                f"(BT: {best.backtest_score:.2f}%, FT: {best.forward_score:.2f}%)")
            
            # Селекция лучших (верхние 50%)
            elite_size = population_size // 2
            elite = [result.params for result in generation_results[:elite_size]]
            
            # Создание нового поколения
            new_population = elite.copy()  # Элита переходит без изменений
            
            # Заполнение остальной популяции потомками и мутантами
            while len(new_population) < population_size:
                if len(new_population) < population_size - 5:  # Кроссовер
                    parent1 = random.choice(elite)
                    parent2 = random.choice(elite)
                    child = self.crossover_params(parent1, parent2)
                    child = self.mutate_params(child, mutation_rate=0.1)
                    new_population.append(child)
                else:  # Случайные особи для разнообразия
                    new_population.append(self.create_random_params())
            
            population = new_population
        
        # Возвращаем лучшие результаты из всех поколений
        best_results.sort(key=lambda x: x.combined_score, reverse=True)
        return best_results
    
    def grid_search_adaptive(self, df: pd.DataFrame, initial_balance: float,
                           forward_test_pct=0.3, iterations=3, 
                           points_per_iteration=50, progress_callback=None) -> List[OptimizationResult]:
        """
        Адаптивный поиск по сетке с уменьшающимися диапазонами
        
        Args:
            df: Исторические данные DataFrame
            initial_balance: Начальный баланс
            forward_test_pct: Процент данных для форвард теста
            iterations: Количество итераций уточнения
            points_per_iteration: Количество точек на итерацию
            progress_callback: Функция для отображения прогресса
        """
        
        # Разделение данных
        split_idx = int(len(df) * (1 - forward_test_pct))
        backtest_df = df.iloc[:split_idx].copy()
        forward_df = df.iloc[split_idx:].copy()
        
        # Текущие границы поиска
        current_bounds = self.param_bounds.copy()
        all_results = []
        
        for iteration in range(iterations):
            if progress_callback:
                progress_callback(f"Итерация {iteration + 1}/{iterations}")
            
            # Генерация точек для текущей итерации с кратными значениями без дубликатов
            test_params_candidates = []
            while len(test_params_candidates) < points_per_iteration * 2:  # Генерируем больше кандидатов
                # Используем кратные значения вместо случайных float
                grid_range_options = list(range(5, 55, 5))  # [5, 10, 15, ..., 50]
                grid_step_options = [round(x * 0.5, 1) for x in range(1, 11)]  # [0.5, 1.0, 1.5, ..., 5.0]
                stop_loss_options = [0.0, 5.0, 10.0, 15.0]
                
                params = OptimizationParams(
                    grid_range_pct=float(random.choice(grid_range_options)),
                    grid_step_pct=random.choice(grid_step_options),
                    stop_loss_pct=random.choice(stop_loss_options)
                )
                test_params_candidates.append(params)
            
            # Удаляем дубликаты и берем нужное количество
            test_params = self.remove_duplicate_params(test_params_candidates)[:points_per_iteration]
            
            # Если после удаления дубликатов недостаточно параметров, добавляем случайные
            while len(test_params) < points_per_iteration:
                test_params.append(self.create_random_params())
            
            # Тестирование в многопоточном режиме
            iteration_results = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_params = {
                    executor.submit(
                        self.evaluate_params, 
                        params, 
                        backtest_df, 
                        forward_df, 
                        initial_balance
                    ): params for params in test_params
                }
                
                for future in as_completed(future_to_params):
                    result = future.result()
                    iteration_results.append(result)
            
            # Сортировка и добавление к общим результатам
            iteration_results.sort(key=lambda x: x.combined_score, reverse=True)
            all_results.extend(iteration_results)
            
            # Обновление границ поиска на основе лучших результатов
            if iteration < iterations - 1:  # Не на последней итерации
                top_results = iteration_results[:max(1, points_per_iteration // 5)]  # Топ 20%
                
                # Вычисление новых границ как ±25% от лучших значений
                best_ranges = [r.params.grid_range_pct for r in top_results]
                best_steps = [r.params.grid_step_pct for r in top_results]
                best_stops = [r.params.stop_loss_pct for r in top_results]
                
                range_center = np.mean(best_ranges)
                step_center = np.mean(best_steps)
                stop_center = np.mean(best_stops)
                
                range_span = (max(best_ranges) - min(best_ranges)) / 2 + 1
                step_span = (max(best_steps) - min(best_steps)) / 2 + 0.1
                stop_span = (max(best_stops) - min(best_stops)) / 2 + 1
                
                current_bounds = {
                    'grid_range_pct': (
                        max(self.param_bounds['grid_range_pct'][0], range_center - range_span),
                        min(self.param_bounds['grid_range_pct'][1], range_center + range_span)
                    ),
                    'grid_step_pct': (
                        max(self.param_bounds['grid_step_pct'][0], step_center - step_span),
                        min(self.param_bounds['grid_step_pct'][1], step_center + step_span)
                    ),
                    'stop_loss_pct': (
                        max(self.param_bounds['stop_loss_pct'][0], stop_center - stop_span),
                        min(self.param_bounds['stop_loss_pct'][1], stop_center + stop_span)
                    )
                }
                
                if progress_callback:
                    best = iteration_results[0]
                    progress_callback(f"Лучший результат итерации: {best.combined_score:.2f}% "
                                    f"Новые границы: Range {current_bounds['grid_range_pct']}, "
                                    f"Step {current_bounds['grid_step_pct']}")
        
        # Сортировка всех результатов
        all_results.sort(key=lambda x: x.combined_score, reverse=True)
        return all_results
