"""
Модуль для анализа и отбора торговых пар, оптимальных для сеточной торговли.
Оценивает параметры волатильности, ликвидности и прогнозируемой доходности.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from binance.client import Client
import sys
import os
import csv
import json

# Добавляем родительский каталог в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.collector import BinanceDataCollector


class GridAnalyzer:
    """
    Класс для анализа пар и определения их пригодности для сеточной торговли.
    """
    
    def __init__(self, collector: BinanceDataCollector):
        """
        Инициализация анализатора сеточной торговли.
        
        Args:
            collector: Экземпляр класса BinanceDataCollector для сбора данных
        """
        self.collector = collector
        self.client = collector.client
        self.pairs_analysis = {}
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Расчет Average True Range (ATR) для определения волатильности.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            period: Период для расчета ATR
            
        Returns:
            Значение ATR в процентах от текущей цены
        """
        # Расчет ATR более надежным способом
        df_tr = df.copy()
        df_tr['prev_close'] = df['close'].shift(1)
        df_tr['tr1'] = df['high'] - df['low']
        df_tr['tr2'] = abs(df['high'] - df_tr['prev_close'])
        df_tr['tr3'] = abs(df['low'] - df_tr['prev_close'])
        df_tr['true_range'] = df_tr[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        atr = df_tr['true_range'].rolling(period).mean().dropna().iloc[-1]
        
        # Возвращаем ATR в процентах от текущей цены
        current_price = df['close'].iloc[-1]
        return (atr / current_price) * 100
    
    def count_price_spikes(self, df: pd.DataFrame, threshold: float = 10.0) -> int:
        """
        Подсчет количества "молний" (резких движений цены) за период.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            threshold: Порог изменения цены в процентах для определения "молнии"
            
        Returns:
            Количество найденных резких движений
        """
        # Расчет дневных изменений High-Low в процентах
        df['daily_range_pct'] = (df['high'] - df['low']) / df['low'] * 100
        
        # Подсчет дней с изменением цены выше порога
        spikes_count = len(df[df['daily_range_pct'] > threshold])
        
        return spikes_count
    
    def get_orderbook_depth(self, symbol: str, limit: int = 500) -> Dict[str, Any]:
        """
        Получение данных о глубине стакана для оценки ликвидности.
        
        Args:
            symbol: Торговая пара
            limit: Количество ордеров в стакане
            
        Returns:
            Словарь с информацией о ликвидности стакана
        """
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            
            # Расчет суммарного объема в пределах 5% от текущей цены
            current_price = float(depth['bids'][0][0])
            price_5pct_down = current_price * 0.95
            price_5pct_up = current_price * 1.05
            
            bid_volume = sum([float(bid[1]) for bid in depth['bids'] 
                              if float(bid[0]) >= price_5pct_down])
            ask_volume = sum([float(ask[1]) for ask in depth['asks'] 
                              if float(ask[0]) <= price_5pct_up])
            
            return {
                'current_price': current_price,
                'bid_volume_5pct': bid_volume,
                'ask_volume_5pct': ask_volume,
                'total_volume_5pct': bid_volume + ask_volume,
                'bid_count': len(depth['bids']),
                'ask_count': len(depth['asks'])
            }
        except Exception as e:
            print(f"Ошибка при получении данных стакана для {symbol}: {e}")
            return {
                'current_price': 0,
                'bid_volume_5pct': 0,
                'ask_volume_5pct': 0,
                'total_volume_5pct': 0,
                'bid_count': 0,
                'ask_count': 0
            }
    
    def estimate_grid_profitability(self, 
                                   df: pd.DataFrame, 
                                   symbol: str,
                                   grid_range_pct: float = 20.0, 
                                   grid_step_pct: float = 1.0,
                                   commission_pct: float = 0.1) -> Dict[str, Any]:
        """
        Оценка потенциальной доходности сеточной стратегии на паре.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            symbol: Торговая пара
            grid_range_pct: Диапазон сетки в процентах (±range/2 от текущей цены)
            grid_step_pct: Шаг сетки в процентах
            commission_pct: Комиссия биржи в процентах
            
        Returns:
            Словарь с оценкой доходности и параметрами сетки
        """
        # Текущая цена
        current_price = df['close'].iloc[-1]
        
        # Расчет количества уровней сетки
        levels = int(grid_range_pct / grid_step_pct)
        
        # Расчет среднего дневного диапазона
        df['daily_range_pct'] = (df['high'] - df['low']) / df['low'] * 100
        avg_daily_range_pct = df['daily_range_pct'].mean()
        
        # Ожидаемое количество сделок за 30 дней
        expected_daily_trades = avg_daily_range_pct / grid_step_pct
        expected_monthly_trades = expected_daily_trades * 30
        
        # Потенциальная доходность за 30 дней (с учетом комиссий)
        profit_per_trade_pct = grid_step_pct - commission_pct
        potential_monthly_profit_pct = expected_monthly_trades * profit_per_trade_pct
        
        # Оценка рисков "молний"
        spikes = self.count_price_spikes(df, threshold=10.0)
        spikes_per_month = spikes / (len(df) / 30)  # Нормализация на 30 дней
        
        # Оценка ликвидности
        liquidity = self.get_orderbook_depth(symbol)
        
        # Рассчитываем рекомендуемый шаг сетки на основе ATR
        atr_pct = self.calculate_atr(df)
        recommended_step_pct = max(atr_pct / 3, 0.5)  # Не менее 0.5%
        
        # Определяем риск на основе частоты "молний"
        risk_level_text = 'низкий' if spikes_per_month <= 1 else 'средний' if spikes_per_month <= 3 else 'высокий'
        
        # Определяем привлекательность для сеточной торговли
        attractiveness_text = 'высокая' if potential_monthly_profit_pct > 15 and spikes_per_month <= 2 else \
                           'средняя' if potential_monthly_profit_pct > 10 and spikes_per_month <= 3 else 'низкая'
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'atr_pct': atr_pct,
            'recommended_step_pct': recommended_step_pct,
            'grid_levels': levels,
            'avg_daily_range_pct': avg_daily_range_pct,
            'expected_daily_trades': expected_daily_trades,
            'expected_monthly_trades': expected_monthly_trades,
            'potential_monthly_profit_pct': potential_monthly_profit_pct,
            'price_spikes_count': spikes,
            'price_spikes_per_month': spikes_per_month,
            'liquidity_5pct': liquidity['total_volume_5pct'],
            'risk_level_text': risk_level_text,
            'attractiveness_text': attractiveness_text
        }
    
    def analyze_pair_for_grid(self, 
                           symbol: str, 
                           days: int = 30,
                           grid_range_pct: float = 20.0,
                           min_liquidity: float = 10000.0) -> Optional[Dict[str, Any]]:
        """
        Комплексный анализ пары для сеточной торговли.
        
        Args:
            symbol: Торговая пара
            days: Количество дней для анализа
            grid_range_pct: Диапазон сетки в процентах
            min_liquidity: Минимальный объем в стакане в USDT
            
        Returns:
            Словарь с результатами анализа или None при ошибке
        """
        try:
            # Получаем исторические данные
            df = self.collector.get_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, days)
            
            if df.empty:
                print(f"Нет данных для {symbol}")
                return None
            
            # Рассчитываем ATR и рекомендуемый шаг сетки
            atr_pct = self.calculate_atr(df)
            recommended_step_pct = max(atr_pct / 3, 0.5)  # Не менее 0.5%
            
            # Оцениваем доходность с рекомендуемым шагом
            grid_analysis = self.estimate_grid_profitability(
                df, symbol, grid_range_pct, recommended_step_pct
            )
            
            # Проверяем ликвидность
            if grid_analysis['liquidity_5pct'] < min_liquidity:
                print(f"Недостаточная ликвидность для {symbol}: {grid_analysis['liquidity_5pct']} < {min_liquidity}")
                return None
            
            # Сохраняем результаты
            self.pairs_analysis[symbol] = grid_analysis
            return grid_analysis
            
        except Exception as e:
            print(f"Ошибка при анализе {symbol} для сеточной торговли: {e}")
            return None
    
    def analyze_pairs_batch(self, 
                          symbols: List[str], 
                          days: int = 30,
                          grid_range_pct: float = 20.0,
                          min_liquidity: float = 10000.0) -> pd.DataFrame:
        """
        Анализ пакета пар для сеточной торговли.
        
        Args:
            symbols: Список торговых пар для анализа
            days: Количество дней для анализа
            grid_range_pct: Диапазон сетки в процентах
            min_liquidity: Минимальный объем в стакане
            
        Returns:
            DataFrame с результатами анализа
        """
        results = []
        total_pairs = len(symbols)
        
        print(f"Начинаем анализ {total_pairs} пар для сеточной торговли...")
        
        for i, symbol in enumerate(symbols):
            print(f"Анализ пары {i+1}/{total_pairs}: {symbol}")
            
            analysis = self.analyze_pair_for_grid(
                symbol, days, grid_range_pct, min_liquidity
            )
            
            if analysis:
                results.append(analysis)
                print(f"Пара {symbol} проанализирована: доходность {analysis['potential_monthly_profit_pct']:.2f}%, "
                      f"риск: {analysis['risk_level_text']}")
            else:
                print(f"Пара {symbol} не прошла анализ для сеточной торговли")
                
        # Создаем DataFrame из результатов
        if results:
            df_results = pd.DataFrame(results)
              # Сортируем по соотношению доходность/риск (привлекательности)
            attractiveness_map = {'высокая': 3, 'средняя': 2, 'низкая': 1}
            df_results['attractiveness_score'] = df_results['attractiveness_text'].map(attractiveness_map)
            df_results.sort_values(by=['attractiveness_score', 'potential_monthly_profit_pct'], 
                                  ascending=[False, False], inplace=True)
            
            print(f"Анализ завершен. Отобрано {len(df_results)} пар для сеточной торговли")
            return df_results
        else:
            print("Не найдено подходящих пар для сеточной торговли")
            return pd.DataFrame()
    
    def get_best_grid_pairs(self, symbols: List[str], top_n: int = 10) -> pd.DataFrame:
        """
        Получение лучших пар для сеточной торговли.
        
        Args:
            symbols: Список торговых пар для анализа
            top_n: Количество лучших пар для возврата
            
        Returns:
            DataFrame с лучшими парами для сеточной торговли
        """
        results_df = self.analyze_pairs_batch(symbols)        
        if not results_df.empty:
            # Возвращаем top_n пар с лучшим соотношением доходность/риск
            return results_df.head(top_n)
        return pd.DataFrame()
    
    def _process_path_segment(self, p_from: float, p_to: float, timestamp: Any,
                              open_orders_long: Dict, open_orders_short: Dict,
                              balance_long: float, balance_short: float,
                              trade_log_long: List, trade_log_short: List,
                              long_grid_prices: List[float], short_grid_prices: List[float],
                              order_size_usd_long: float, order_size_usd_short: float,
                              grid_step_pct: float, commission_pct: float,
                              debug: bool = False, candle_counter: Any = 0):
        """
        Обрабатывает один сегмент движения цены внутри свечи (например, от open до low).
        Собирает все возможные события (открытие/закрытие ордеров), сортирует их по цене
        и исполняет в правильном порядке.
        """
        min_p, max_p = min(p_from, p_to), max(p_from, p_to)
        direction = 'up' if p_to > p_from else 'down'

        events = []

        # 1. Собрать события на открытие ордеров
        for price in long_grid_prices:
            if min_p <= price <= max_p:
                events.append({'price': price, 'type': 'open', 'side': 'long'})
        for price in short_grid_prices:
            if min_p <= price <= max_p:
                events.append({'price': price, 'type': 'open', 'side': 'short'})

        # 2. Собрать события на закрытие (Take Profit)
        for entry_price, size in list(open_orders_long.items()):
            tp_price = entry_price * (1 + grid_step_pct / 100)
            if min_p <= tp_price <= max_p:
                events.append({'price': tp_price, 'type': 'close', 'side': 'long', 'entry_price': entry_price, 'size': size})
        
        for entry_price, size in list(open_orders_short.items()):
            tp_price = entry_price * (1 - grid_step_pct / 100)
            if min_p <= tp_price <= max_p:
                events.append({'price': tp_price, 'type': 'close', 'side': 'short', 'entry_price': entry_price, 'size': size})

        # 3. Сортировать события по цене в направлении движения
        events.sort(key=lambda x: x['price'], reverse=(direction == 'down'))
        if debug and events:
            print(f"  -> Обработка сегмента: {p_from:.4f} -> {p_to:.4f} (Направление: {direction})")
            print(f"     События на сегменте: {[f'{e['type']}/{e['side']}@{e['price']:.4f}' for e in events]}")

        # 4. Исполнить события
        for event in events:
            price = event['price'] # Извлекаем цену из события
                        
            if event['type'] == 'open':
                
                if event['side'] == 'long' and price not in open_orders_long:
                    if order_size_usd_long <= 0: continue
                    # Проверяем, хватает ли средств на покупку и комиссию
                    commission = order_size_usd_long * (commission_pct / 100)
                    if balance_long < (order_size_usd_long + commission):
                        if debug:
                            print(f"       * Недостаточно средств для открытия Long @ {price:.4f}. Баланс: ${balance_long:.2f}, Требуется: ${order_size_usd_long + commission:.2f}")
                        continue
                        
                    size = order_size_usd_long / price
                    
                    # Вычитаем из баланса стоимость позиции и комиссию
                    balance_long -= order_size_usd_long + commission
                    open_orders_long[price] = size
                    
                    log_entry = {
                        'timestamp': timestamp, 
                        'type': 'Открытие Long', 
                        'price': price, 
                        'amount_usd': order_size_usd_long, 
                        'commission_usd': commission, 
                        'balance_usd': balance_long
                    }
                    trade_log_long.append(log_entry)
                    
                    if debug:
                        print(f"       * EXEC: {log_entry['type']} @ {log_entry['price']:.4f}, SizeUSD: {log_entry['amount_usd']:.2f}, "
                              f"Комиссия: {log_entry['commission_usd']:.4f}, Новый баланс: ${log_entry['balance_usd']:.2f}")

                elif event['side'] == 'short' and price not in open_orders_short:
                    if order_size_usd_short <= 0: continue
                    
                    # Для Short используем маржинальную торговлю (требуется маржа)
                    margin_requirement = 0.10  # 10% от стоимости позиции как маржа
                    required_margin = order_size_usd_short * margin_requirement
                    commission = order_size_usd_short * (commission_pct / 100)
                    
                    # Проверяем, хватает ли средств на маржу и комиссию
                    if balance_short < (required_margin + commission):
                        if debug:
                            print(f"       * Недостаточно средств для открытия Short @ {price:.4f}. Баланс: ${balance_short:.2f}, "
                                  f"Требуется маржа: ${required_margin:.2f}, Комиссия: ${commission:.2f}")
                        continue
                    
                    size = order_size_usd_short / price
                    
                    # Вычитаем из баланса маржу и комиссию
                    balance_short -= (required_margin + commission)
                    open_orders_short[price] = size
                    
                    log_entry = {
                        'timestamp': timestamp, 
                        'type': 'Открытие Short', 
                        'price': price, 
                        'amount_usd': order_size_usd_short, 
                        'margin_usd': required_margin,
                        'commission_usd': commission, 
                        'balance_usd': balance_short
                    }
                    trade_log_short.append(log_entry)
                    
                    if debug:
                        print(f"       * EXEC: {log_entry['type']} @ {log_entry['price']:.4f}, SizeUSD: {log_entry['amount_usd']:.2f}, "
                              f"Маржа: ${log_entry['margin_usd']:.2f}, Комиссия: {log_entry['commission_usd']:.4f}, "
                              f"Новый баланс: ${log_entry['balance_usd']:.2f}")

            elif event['type'] == 'close':
                entry_price = event['entry_price']
                size = event['size']
                
                if event['side'] == 'long' and entry_price in open_orders_long:
                    # Рассчитываем PnL
                    entry_value = entry_price * size
                    exit_value = price * size
                    profit = exit_value - entry_value
                    commission_entry = entry_value * (commission_pct / 100)
                    commission_exit = exit_value * (commission_pct / 100)
                    total_commission = commission_entry + commission_exit
                    net_profit = profit - total_commission
                    
                    # Возвращаем на баланс стоимость продажи за вычетом комиссии
                    balance_long += exit_value - commission_exit
                    
                    # Удаляем ордер
                    del open_orders_long[entry_price]
                    
                    # Логируем сделку
                    log_entry = {
                        'timestamp': timestamp,
                        'type': 'Закрытие Long',
                        'price': price,
                        'entry_price': entry_price,
                        'amount_usd': entry_value,
                        'exit_value_usd': exit_value,
                        'profit_usd': profit,
                        'commission_usd': total_commission,
                        'net_pnl_usd': net_profit,
                        'balance_usd': balance_long
                    }
                    trade_log_long.append(log_entry)
                    if debug:
                        print(f"       * EXEC: {log_entry['type']} @ {log_entry['price']:.4f} (from {log_entry['entry_price']:.4f}), " 
                              f"PnL: {log_entry['net_pnl_usd']:.4f}, Комиссия: {log_entry['commission_usd']:.4f}, "
                              f"New Balance: {log_entry['balance_usd']:.2f}")

                elif event['side'] == 'short' and entry_price in open_orders_short:
                    # Рассчитываем PnL
                    entry_value = entry_price * size
                    exit_value = price * size
                    profit = entry_value - exit_value
                    commission_entry = entry_value * (commission_pct / 100)
                    commission_exit = exit_value * (commission_pct / 100)
                    total_commission = commission_entry + commission_exit
                    net_profit = profit - total_commission

                    # Возвращаем маржу и добавляем PnL
                    margin_requirement = 0.10 
                    margin_returned = entry_value * margin_requirement
                    balance_short += margin_returned + net_profit
                    
                    # Удаляем ордер
                    del open_orders_short[entry_price]
                    
                    # Логируем сделку
                    log_entry = {
                        'timestamp': timestamp,
                        'type': 'Закрытие Short',
                        'price': price,
                        'entry_price': entry_price,
                        'amount_usd': entry_value,
                        'exit_value_usd': exit_value,
                        'profit_usd': profit,
                        'commission_usd': total_commission,
                        'net_pnl_usd': net_profit,
                        'balance_usd': balance_short
                    }
                    trade_log_short.append(log_entry)
                    if debug:
                        print(f"       * EXEC: {log_entry['type']} @ {log_entry['price']:.4f} (from {log_entry['entry_price']:.4f}), " 
                              f"PnL: {log_entry['net_pnl_usd']:.4f}, Комиссия: {log_entry['commission_usd']:.4f}, "
                              f"New Balance: {log_entry['balance_usd']:.2f}")

        return balance_long, balance_short

    def estimate_dual_grid_by_candles_realistic(self, 
        df: pd.DataFrame,
        initial_balance_long: float = 1000.0,
        initial_balance_short: float = 1000.0,
        order_size_usd_long: float = 100.0,
        order_size_usd_short: float = 100.0,
        grid_range_pct: float = 20.0,
        grid_step_pct: float = 1.0,
        commission_pct: float = 0.1,
        stop_loss_pct: Optional[float] = None,
        stop_loss_strategy: str = 'none',
        debug: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Симулирует дуальную сеточную стратегию (Long/Short) на исторических данных (OHLCV).
        Каждая сделка учитывает комиссии, реальное распределение средств и плавающий PnL.

        Args:
            df: DataFrame с историческими данными (OHLCV).
            initial_balance_long: Начальный баланс для Long-стратегии.
            initial_balance_short: Начальный баланс для Short-стратегии.
            order_size_usd_long: Размер ордера в USD для Long.
            order_size_usd_short: Размер ордера в USD для Short.
            grid_range_pct: Диапазон сетки в процентах.
            grid_step_pct: Шаг сетки в процентах.
            commission_pct: Комиссия биржи в процентах.
            stop_loss_pct: Процент стоп-лосса.
            stop_loss_strategy: Стратегия стоп-лосса ('none', 'reset_grid', 'stop_trading').
            debug: Флаг для вывода отладочной информации.

        Returns:
            Кортеж, содержащий:
            - Словарь со статистикой по Long-стратегии.
            - Словарь со статистикой по Short-стратегии.
            - Журнал сделок для Long.
            - Журнал сделок для Short.
        """
        balance_long = initial_balance_long
        balance_short = initial_balance_short
        open_orders_long: Dict[float, float] = {}
        open_orders_short: Dict[float, float] = {}
        trade_log_long: List[Dict[str, Any]] = []
        trade_log_short: List[Dict[str, Any]] = []

        # Расчет количества уровней и размера ордера
        num_levels = int(grid_range_pct / grid_step_pct) if grid_step_pct > 0 else 0
        if num_levels == 0:
            # Возвращаем пустые результаты, если сетка не может быть создана
            return {}, {}, [], []

        # Автоматический расчет размера ордера, если он не задан (равен 0)
        final_order_size_long = order_size_usd_long
        if final_order_size_long == 0:
            final_order_size_long = initial_balance_long / num_levels

        final_order_size_short = order_size_usd_short
        if final_order_size_short == 0:
            final_order_size_short = initial_balance_short / num_levels

        # Инициализация сеток
        first_price = df['open'].iloc[0]
        long_grid_prices = [first_price * (1 - i * grid_step_pct / 100) for i in range(1, num_levels + 1)]
        short_grid_prices = [first_price * (1 + i * grid_step_pct / 100) for i in range(1, num_levels + 1)]

        if debug:
            print(f"Симуляция запущена. Начальные балансы: Long=${balance_long:.2f}, Short=${balance_short:.2f}")
            print(f"Диапазон: {grid_range_pct}%, Шаг: {grid_step_pct:.2f}%, Уровней: {num_levels}")
            print(f"Размер ордера Long: ${final_order_size_long:.2f}, Short: ${final_order_size_short:.2f}")
            print(f"Первоначальная цена: {first_price:.4f}")
            print(f"Комиссия: {commission_pct:.2f}%")

        # Основной цикл по свечам
        for index, candle in df.iterrows():
            timestamp = candle.name
            o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']

            if debug:
                print(f"\n--- Свеча #{index} ({timestamp}) | O:{o:.4f} H:{h:.4f} L:{l:.4f} C:{c:.4f} ---")

            # Определяем путь цены внутри свечи
            # True если open -> high -> low -> close, False если open -> low -> high -> close
            path_ohlc = abs(h - o) > abs(l - o)

            if path_ohlc:
                # Путь: Open -> High -> Low -> Close
                paths = [(o, h), (h, l), (l, c)]
                if debug:
                    print(f"  Путь свечи: Open -> High -> Low -> Close")
            else:
                # Путь: Open -> Low -> High -> Close
                paths = [(o, l), (l, h), (h, c)]
                if debug:
                    print(f"  Путь свечи: Open -> Low -> High -> Close")

            # Обработка каждого сегмента пути
            for p_from, p_to in paths:
                balance_long, balance_short = self._process_path_segment(
                    p_from, p_to, timestamp,
                    open_orders_long, open_orders_short,
                    balance_long, balance_short,
                    trade_log_long, trade_log_short,
                    long_grid_prices, short_grid_prices,
                    final_order_size_long, final_order_size_short,
                    grid_step_pct, commission_pct, debug, index
                )

            # Проверка стоп-лоссов в конце каждой свечи (если включены)
            if stop_loss_pct is not None and stop_loss_pct > 0:
                # Рассчитываем плавающую прибыль/убыток для всех позиций
                floating_pnl_long = 0
                floating_pnl_short = 0
                initial_investment_long = 0
                initial_investment_short = 0
                
                # Расчет плавающего PнL для Long позиций
                for entry_price, size in list(open_orders_long.items()):
                    entry_value = entry_price * size
                    current_value = c * size
                    initial_investment_long += entry_value
                    floating_pnl_long += current_value - entry_value
                
                # Расчет плавающего PнL для Short позиций
                for entry_price, size in list(open_orders_short.items()):
                    entry_value = entry_price * size
                    current_value = c * size
                    initial_investment_short += entry_value
                    floating_pnl_short += entry_value - current_value

                # Рассчитываем процент убытка от начального баланса
                floating_loss_pct_long = abs(floating_pnl_long) / initial_investment_long * 100 if initial_investment_long > 0 else 0
                floating_loss_pct_short = abs(floating_pnl_short) / initial_investment_short * 100 if initial_investment_short > 0 else 0

                # Проверяем превышение порога стоп-лосса
                stop_loss_triggered_long = floating_loss_pct_long >= stop_loss_pct
                stop_loss_triggered_short = floating_loss_pct_short >= stop_loss_pct

                if debug:
                    if initial_investment_long > 0:
                        print(f"  Long: Инвестировано ${initial_investment_long:.2f}, Плавающий PnL: ${floating_pnl_long:.2f} ({-floating_loss_pct_long:.2f}% убытка)")
                    if initial_investment_short > 0:
                        print(f"  Short: Инвестировано ${initial_investment_short:.2f}, Плавающий PnL: ${floating_pnl_short:.2f} ({-floating_loss_pct_short:.2f}% убытка)")

                # Обработка стоп-лоссов для Long позиций если суммарный убыток превысил порог
                if stop_loss_triggered_long:
                    for entry_price, size in list(open_orders_long.items()):
                        # Закрытие по стоп-лоссу
                        entry_value = entry_price * size
                        exit_value = c * size
                        profit = exit_value - entry_value  # Будет отрицательным значением при убытке
                        commission_entry = entry_value * (commission_pct / 100)
                        commission_exit = exit_value * (commission_pct / 100)
                        total_commission = commission_entry + commission_exit
                        net_profit = profit - total_commission
                        
                        # Возвращаем в баланс только стоимость позиции при продаже минус комиссия
                        balance_long += exit_value - commission_exit
                        
                        # Удаляем ордер
                        del open_orders_long[entry_price]
                        
                        # Логируем сделку
                        log_entry = {
                            'timestamp': timestamp,
                            'type': 'Стоп-лосс Long (Плавающий)',
                            'price': c,
                            'entry_price': entry_price,
                            'amount_usd': entry_value,
                            'exit_value_usd': exit_value,
                            'profit_usd': profit,
                            'commission_usd': total_commission,
                            'net_pnl_usd': net_profit,
                            'balance_usd': balance_long,
                            'note': f"Сработал стоп-лосс {stop_loss_pct}% (общий убыток {floating_loss_pct_long:.2f}%)"
                        }
                        trade_log_long.append(log_entry)
                        if debug:
                            print(f"       * СТОП-ЛОСС Long @ {c:.4f} (from {entry_price:.4f}), " 
                                  f"PnL: {net_profit:.4f}, Комиссия: {total_commission:.4f}, "
                                  f"New Balance: {balance_long:.2f}")
                
                # Обработка стоп-лоссов для Short позиций если суммарный убыток превысил порог
                if stop_loss_triggered_short:
                    for entry_price, size in list(open_orders_short.items()):
                        # Закрытие по стоп-лоссу
                        entry_value = entry_price * size
                        exit_value = c * size
                        profit = entry_value - exit_value  # Будет отрицательным значением при убытке
                        commission_entry = entry_value * (commission_pct / 100)
                        commission_exit = exit_value * (commission_pct / 100)
                        total_commission = commission_entry + commission_exit
                        net_profit = profit - total_commission
                        
                        # Возвращаем маржу и прибыль/убыток
                        margin_requirement = 0.10  # 10% от стоимости позиции как маржа
                        margin_used = entry_value * margin_requirement
                        balance_short += margin_used + net_profit
                        
                        # Удаляем ордер
                        del open_orders_short[entry_price]
                        
                        # Логируем сделку
                        log_entry = {
                            'timestamp': timestamp,
                            'type': 'Стоп-лосс Short (Плавающий)',
                            'price': c,
                            'entry_price': entry_price,
                            'amount_usd': entry_value,
                            'exit_value_usd': exit_value,
                            'profit_usd': profit,
                            'commission_usd': total_commission,
                            'net_pnl_usd': net_profit,
                            'balance_usd': balance_short,
                            'note': f"Сработал стоп-лосс {stop_loss_pct}% (общий убыток {floating_loss_pct_short:.2f}%)"
                        }
                        trade_log_short.append(log_entry)

                        if debug:
                            print(f"       * СТОП-ЛОСС Short @ {c:.4f} (from {entry_price:.4f}), "
                                  f"PnL: {net_profit:.4f}, Комиссия: {total_commission:.4f}, "
                                  f"New Balance: {balance_short:.2f}")
                
                # Перезапуск сетки при необходимости
                if (stop_loss_triggered_long or stop_loss_triggered_short) and stop_loss_strategy == 'reset_grid':
                    long_grid_prices = [c * (1 - i * grid_step_pct / 100) for i in range(1, 100)]
                    short_grid_prices = [c * (1 + i * grid_step_pct / 100) for i in range(1, 100)]
                    if debug:
                        print(f"       * Перезапуск сетки после стоп-лосса. Новая опорная цена: {c:.4f}")
                elif stop_loss_strategy == 'stop_trading':
                    # Очистка всех открытых ордеров
                    open_orders_long.clear()
                    open_orders_short.clear()
                    if debug:
                        print(f"       * Остановка торговли после стоп-лосса.")

        # Закрытие всех открытых ордеров по последней цене
        last_price = df['close'].iloc[-1]
        last_timestamp = df.index[-1]
        
        if debug:
            print(f"\n--- Закрытие всех открытых ордеров по последней цене: {last_price:.4f} ---")
        
        # Закрытие Long ордеров
        for entry_price, size in list(open_orders_long.items()):
            entry_value = entry_price * size
            exit_value = last_price * size
            profit = exit_value - entry_value
            commission_entry = entry_value * (commission_pct / 100)
            commission_exit = exit_value * (commission_pct / 100)
            total_commission = commission_entry + commission_exit
            net_profit = profit - total_commission
            balance_long += exit_value - commission_exit
            
            # Логируем сделку
            log_entry = {
                'timestamp': last_timestamp,
                'type': 'Закрытие Long (Финал)',
                'price': last_price,
                'entry_price': entry_price,
                'amount_usd': entry_value,
                'exit_value_usd': exit_value,
                'profit_usd': profit,
                'commission_usd': total_commission,
                'net_pnl_usd': net_profit,
                'balance_usd': balance_long
            }
            trade_log_long.append(log_entry)
            if debug:
                print(f"   * EXEC: {log_entry['type']} @ {log_entry['price']:.4f} (from {log_entry['entry_price']:.4f}), "
                      f"PnL: {log_entry['net_pnl_usd']:.4f}, Комиссия: {log_entry['commission_usd']:.4f}, "
                      f"New Balance: {log_entry['balance_usd']:.2f}")
        
        # Закрытие Short ордеров
        for entry_price, size in list(open_orders_short.items()):
            entry_value = entry_price * size
            exit_value = last_price * size
            profit = entry_value - exit_value
            commission_entry = entry_value * (commission_pct / 100)
            commission_exit = exit_value * (commission_pct / 100)
            total_commission = commission_entry + commission_exit
            net_profit = profit - total_commission
            
            # Возвращаем маржу и прибыль/убыток
            margin_requirement = 0.10  # 10% от стоимости позиции как маржа
            margin_used = entry_value * margin_requirement
            balance_short += margin_used + net_profit
            
            # Логируем сделку
            log_entry = {
                'timestamp': last_timestamp,
                'type': 'Закрытие Short (Финал)',
                'price': last_price,
                'entry_price': entry_price,
                'amount_usd': entry_value,
                'exit_value_usd': exit_value,
                'profit_usd': profit,
                'commission_usd': total_commission,
                'net_pnl_usd': net_profit,
                'balance_usd': balance_short
            }
            trade_log_short.append(log_entry)
            if debug:
                print(f"       * EXEC: {log_entry['type']} @ {log_entry['price']:.4f} (from {log_entry['entry_price']:.4f}), " 
                      f"PnL: {log_entry['net_pnl_usd']:.4f}, Комиссия: {log_entry['commission_usd']:.4f}, "
                      f"New Balance: {log_entry['balance_usd']:.2f}")

        # Расчет итоговой статистики
        stats_long = {
            'final_balance': balance_long, 
            'total_pnl': balance_long - initial_balance_long,
            'total_pnl_pct': (balance_long - initial_balance_long) / initial_balance_long * 100,
            'trades_count': len(trade_log_long),
            'profitable_trades': sum(1 for trade in trade_log_long if trade.get('net_pnl_usd', 0) > 0),
            'losing_trades': sum(1 for trade in trade_log_long if trade.get('net_pnl_usd', 0) < 0),
            'win_rate': sum(1 for trade in trade_log_long if trade.get('net_pnl_usd', 0) > 0) / len(trade_log_long) * 100 if trade_log_long else 0,
            'total_commission': sum(trade.get('commission_usd', 0) for trade in trade_log_long),
            'avg_profit_per_trade': sum(trade.get('net_pnl_usd', 0) for trade in trade_log_long) / len(trade_log_long) if trade_log_long else 0
        }
        
        stats_short = {
            'final_balance': balance_short, 
            'total_pnl': balance_short - initial_balance_short,
            'total_pnl_pct': (balance_short - initial_balance_short) / initial_balance_short * 100,
            'trades_count': len(trade_log_short),
            'profitable_trades': sum(1 for trade in trade_log_short if trade.get('net_pnl_usd', 0) > 0),
            'losing_trades': sum(1 for trade in trade_log_short if trade.get('net_pnl_usd', 0) < 0),
            'win_rate': sum(1 for trade in trade_log_short if trade.get('net_pnl_usd', 0) > 0) / len(trade_log_short) * 100 if trade_log_short else 0,
            'total_commission': sum(trade.get('commission_usd', 0) for trade in trade_log_short),
            'avg_profit_per_trade': sum(trade.get('net_pnl_usd', 0) for trade in trade_log_short) / len(trade_log_short) if trade_log_short else 0
        }

        if debug:
            print("\n--- Итоговая статистика ---")
            print(f"Long: Баланс=${stats_long['final_balance']:.2f}, PnL=${stats_long['total_pnl']:.2f} ({stats_long['total_pnl_pct']:.2f}%), "
                  f"Сделок={stats_long['trades_count']}, Win={stats_long['win_rate']:.2f}%, "
                  f"Комиссии=${stats_long['total_commission']:.2f}")
            print(f"Short: Баланс=${stats_short['final_balance']:.2f}, PnL=${stats_short['total_pnl']:.2f} ({stats_short['total_pnl_pct']:.2f}%), "
                  f"Сделок={stats_short['trades_count']}, Win={stats_short['win_rate']:.2f}%, "
                  f"Комиссии=${stats_short['total_commission']:.2f}")
            print(f"Итого: Совокупный PnL=${stats_long['total_pnl'] + stats_short['total_pnl']:.2f} "
                  f"({(stats_long['total_pnl_pct'] + stats_short['total_pnl_pct'])/2:.2f}%)")

        return stats_long, stats_short, trade_log_long, trade_log_short
    

if __name__ == "__main__":
    # Этот блок можно использовать для локального тестирования модуля.
    # Например, создать экземпляр GridAnalyzer и вызвать его методы.
    
    # Пример:
    # collector = BinanceDataCollector(api_key="your_key", api_secret="your_secret")
    # analyzer = GridAnalyzer(collector)
    # analyzer.find_best_pairs_for_grid_trading()
    pass # Оставляем пустым, чтобы избежать выполнения тестов при импорте
