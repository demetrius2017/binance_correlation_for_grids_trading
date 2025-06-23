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
    
    def estimate_dual_grid_by_candles(self,
                                     df: pd.DataFrame,
                                     grid_range_pct: float = 20.0,
                                     grid_step_pct: float = 1.0,
                                     commission_pct: float = 0.1,
                                     stop_loss_pct: float = 5.0,
                                     lightning_compensation: float = 30.0) -> Dict[str, Any]:
        """
        Приближённая симуляция двух сеток (long + short) по дневным свечам.
        Учёт проторговок тенями и убытков телами свечей, а также выхода за пределы сетки.
        Детальное отслеживание убытков по стоп-лоссу и молниям с компенсацией.        """
        total_long = 0.0
        total_short = 0.0
        breaks = 0
          # Счетчики сделок (раздельно для каждой сетки)
        total_trades_long = 0
        total_trades_short = 0
        profitable_trades_long = 0
        profitable_trades_short = 0
        losing_trades_long = 0
        losing_trades_short = 0
        
        # Детальная статистика убытков
        stop_loss_stats = {
            'long': {'count': 0, 'total_loss': 0.0, 'avg_loss': 0.0},
            'short': {'count': 0, 'total_loss': 0.0, 'avg_loss': 0.0}
        }
        
        lightning_stats = {
            'long': {'count': 0, 'total_loss': 0.0, 'total_compensation': 0.0, 'net_loss': 0.0},
            'short': {'count': 0, 'total_loss': 0.0, 'total_compensation': 0.0, 'net_loss': 0.0}
        }
        
        # Расчет шага сетки на основе ATR
        atr_pct = self.calculate_atr(df)
        recommended_step = max(atr_pct / 3, 0.5)
        actual_step = grid_step_pct if grid_step_pct > 0 else recommended_step
        
        # Выводим отладочную информацию
        print(f"Рекомендуемый шаг сетки: {recommended_step:.2f}%")
        print(f"Используемый шаг сетки: {actual_step:.2f}%")
        
        # Расчет верхней и нижней границ сетки относительно начальной цены
        initial_price = df.iloc[0]['close']
        upper_bound = initial_price * (1 + grid_range_pct / 100)
        lower_bound = initial_price * (1 - grid_range_pct / 100)
        
        for i, (_, row) in enumerate(df.iterrows()):
            open_p, high_p, low_p, close_p = row['open'], row['high'], row['low'], row['close']
            base = min(open_p, close_p)
            
            # Проверка на выход за пределы сетки (молнии)
            lightning_triggered = False
            lightning_loss_long = 0.0
            lightning_loss_short = 0.0
            
            if high_p > upper_bound:
                lightning_triggered = True
                lightning_loss_long = (high_p - upper_bound) / upper_bound * 100
                lightning_stats['long']['count'] += 1
                lightning_stats['long']['total_loss'] += lightning_loss_long
                
                # Применяем компенсацию
                compensation = lightning_loss_long * (lightning_compensation / 100)
                lightning_stats['long']['total_compensation'] += compensation
                lightning_stats['long']['net_loss'] += lightning_loss_long - compensation
                
            if low_p < lower_bound:
                lightning_triggered = True
                lightning_loss_short = (lower_bound - low_p) / lower_bound * 100
                lightning_stats['short']['count'] += 1
                lightning_stats['short']['total_loss'] += lightning_loss_short
                
                # Применяем компенсацию
                compensation = lightning_loss_short * (lightning_compensation / 100)
                lightning_stats['short']['total_compensation'] += compensation
                lightning_stats['short']['net_loss'] += lightning_loss_short - compensation
            
            # Проверка стоп-лосса
            stop_loss_triggered_long = False
            stop_loss_triggered_short = False
            stop_loss_long = 0.0
            stop_loss_short = 0.0
              # Стоп-лосс для long позиций (падение цены)
            price_drop_pct = (open_p - low_p) / open_p * 100
            if price_drop_pct > stop_loss_pct:
                stop_loss_triggered_long = True
                # Применяем компенсацию к стоп-лоссу
                compensated_loss = price_drop_pct * (1 - lightning_compensation / 100)
                stop_loss_long = compensated_loss
                stop_loss_stats['long']['count'] += 1
                stop_loss_stats['long']['total_loss'] += price_drop_pct  # Первоначальная потеря
            
            # Стоп-лосс для short позиций (рост цены)
            price_rise_pct = (high_p - open_p) / open_p * 100
            if price_rise_pct > stop_loss_pct:
                stop_loss_triggered_short = True
                # Применяем компенсацию к стоп-лоссу
                compensated_loss = price_rise_pct * (1 - lightning_compensation / 100)
                stop_loss_short = compensated_loss
                stop_loss_stats['short']['count'] += 1
                stop_loss_stats['short']['total_loss'] += price_rise_pct  # Первоначальная потеря
            
            # Если сработали стопы или молнии, уменьшаем профит
            if lightning_triggered or stop_loss_triggered_long or stop_loss_triggered_short:
                breaks += 1
              # расчёт тел и теней в процентах
            body_pct = abs(close_p - open_p) / base * 100
            upper_wick_pct = (high_p - max(open_p, close_p)) / base * 100
            lower_wick_pct = (min(open_p, close_p) - low_p) / low_p * 100
              # ИСПРАВЛЕНА ЛОГИКА: берем только кратную шагу часть тени
            # Количество полных шагов в тенях
            upper_wick_trades = int(upper_wick_pct / actual_step)
            lower_wick_trades = int(lower_wick_pct / actual_step)
              # Подсчет сделок - КАЖДАЯ ТЕНЬ РАБОТАЕТ ДЛЯ ОБЕИХ СЕТОК
            # Верхняя тень: сделки для Long (покупает дешевле) и Short (продает дороже)
            total_trades_long += upper_wick_trades
            total_trades_short += upper_wick_trades
            profitable_trades_long += upper_wick_trades  # Тени всегда прибыльны
            profitable_trades_short += upper_wick_trades
            
            # Нижняя тень: сделки для Long (продает дороже) и Short (покупает дешевле)  
            total_trades_long += lower_wick_trades
            total_trades_short += lower_wick_trades
            profitable_trades_long += lower_wick_trades  # Тени всегда прибыльны
            profitable_trades_short += lower_wick_trades
            
            # Фактически отработанная часть теней (только кратная шагу)
            upper_wick_traded_pct = upper_wick_trades * actual_step
            lower_wick_traded_pct = lower_wick_trades * actual_step
            total_wick_traded_pct = upper_wick_traded_pct + lower_wick_traded_pct
            
            # Профит с теней = только с отработанной части минус комиссии
            profit_wicks = total_wick_traded_pct - (upper_wick_trades + lower_wick_trades) * commission_pct
            
            # убыток тел из-за одностороннего движения
            is_red_candle = close_p < open_p
            is_green_candle = close_p > open_p
            
            # Количество шагов сетки в теле свечи
            body_steps = int(body_pct / actual_step)
              # Расчет профита/убытка от тела свечи
            long_body_pnl = -body_steps * actual_step if is_red_candle else 0  # Long теряет на падении
            short_body_pnl = -body_steps * actual_step if is_green_candle else 0  # Short теряет на росте
              # Подсчет убыточных сделок по телам - ТОЛЬКО ДЛЯ ОДНОЙ СЕТКИ
            if is_red_candle and body_steps > 0:
                # Красная свеча = убыток только для Long сетки
                total_trades_long += body_steps
                losing_trades_long += body_steps
            if is_green_candle and body_steps > 0:
                # Зеленая свеча = убыток только для Short сетки
                total_trades_short += body_steps  
                losing_trades_short += body_steps
            
            # Суммируем для двух сеток с учетом стоп-лоссов и молний
            long_pnl = profit_wicks + long_body_pnl - stop_loss_long - lightning_stats['long']['net_loss']
            short_pnl = profit_wicks + short_body_pnl - stop_loss_short - lightning_stats['short']['net_loss']
            
            # Обновляем общие суммы
            total_long += long_pnl
            total_short += short_pnl            # Отладочная информация для первых 3 свечей
            if i < 3:
                wick_trades_total = upper_wick_trades + lower_wick_trades
                body_trades = body_steps if (is_red_candle or is_green_candle) else 0
                print(f"Свеча {i+1}: Body: {body_pct:.2f}%, Upper Wick: {upper_wick_pct:.2f}%, Lower Wick: {lower_wick_pct:.2f}%")
                print(f"  Шагов в теле: {body_steps}, в верхней тени: {upper_wick_trades}, в нижней тени: {lower_wick_trades}")
                print(f"  Сделки: тени {wick_trades_total} (по {wick_trades_total} для каждой сетки), тела {body_trades} (только одна сетка)")
                print(f"  Отработано: верхняя тень {upper_wick_traded_pct:.2f}% из {upper_wick_pct:.2f}%, нижняя тень {lower_wick_traded_pct:.2f}% из {lower_wick_pct:.2f}%")
                print(f"  Недоработано: верхняя тень {upper_wick_pct - upper_wick_traded_pct:.2f}%, нижняя тень {lower_wick_pct - lower_wick_traded_pct:.2f}%")
                print(f"  PnL Long: {long_pnl:.2f}%, PnL Short: {short_pnl:.2f}%")
                if stop_loss_triggered_long or stop_loss_triggered_short:
                    print(f"  Стоп-лосс: Long: {stop_loss_long:.2f}%, Short: {stop_loss_short:.2f}%")
                if lightning_triggered:
                    print(f"  Молния: Long: {lightning_loss_long:.2f}%, Short: {lightning_loss_short:.2f}%")
          # Рассчитываем средние убытки
        if stop_loss_stats['long']['count'] > 0:
            stop_loss_stats['long']['avg_loss'] = stop_loss_stats['long']['total_loss'] / stop_loss_stats['long']['count']
        if stop_loss_stats['short']['count'] > 0:
            stop_loss_stats['short']['avg_loss'] = stop_loss_stats['short']['total_loss'] / stop_loss_stats['short']['count']
        
        return {
            'combined_pct': total_long + total_short,
            'long_pct': total_long,
            'short_pct': total_short,
            'breaks': breaks,
            'grid_step_pct': actual_step,
            'grid_step_used': actual_step,
            'commission_pct': commission_pct,
            'stop_loss_pct': stop_loss_pct,
            'lightning_compensation': lightning_compensation,
              # Информация о сделках - раздельная статистика
            'total_trades_long': total_trades_long,
            'total_trades_short': total_trades_short,
            'total_trades': total_trades_long + total_trades_short,
            'profitable_trades_long': profitable_trades_long,
            'profitable_trades_short': profitable_trades_short,
            'profitable_trades': profitable_trades_long + profitable_trades_short,
            'losing_trades_long': losing_trades_long,
            'losing_trades_short': losing_trades_short,
            'losing_trades': losing_trades_long + losing_trades_short,
            'win_rate_long': (profitable_trades_long / total_trades_long * 100) if total_trades_long > 0 else 0,
            'win_rate_short': (profitable_trades_short / total_trades_short * 100) if total_trades_short > 0 else 0,
            'win_rate': ((profitable_trades_long + profitable_trades_short) / (total_trades_long + total_trades_short) * 100) if (total_trades_long + total_trades_short) > 0 else 0,
            
            # Детальная статистика стоп-лоссов
            'stop_loss_stats': stop_loss_stats,
            'total_stop_loss_count': stop_loss_stats['long']['count'] + stop_loss_stats['short']['count'],
            'total_stop_loss_amount': stop_loss_stats['long']['total_loss'] + stop_loss_stats['short']['total_loss'],
            
            # Детальная статистика молний
            'lightning_stats': lightning_stats,
            'total_lightning_count': lightning_stats['long']['count'] + lightning_stats['short']['count'],
            'total_lightning_loss': lightning_stats['long']['total_loss'] + lightning_stats['short']['total_loss'],
            'total_lightning_compensation': lightning_stats['long']['total_compensation'] + lightning_stats['short']['total_compensation'],
            'total_lightning_net_loss': lightning_stats['long']['net_loss'] + lightning_stats['short']['net_loss'],
            
            # Границы сетки
            'upper_bound': upper_bound,
            'lower_bound': lower_bound,
            'initial_price': initial_price
        }
    

if __name__ == "__main__":
    # Пример использования
    import json
    
    # Загрузка API ключей из файла конфигурации
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            api_key = config.get("api_key", "")
            api_secret = config.get("api_secret", "")
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        api_key = "YOUR_API_KEY"
        api_secret = "YOUR_API_SECRET"
    
    collector = BinanceDataCollector(api_key, api_secret)
    grid_analyzer = GridAnalyzer(collector)
    
    # Получаем пары старше 1 года
    old_pairs = collector.get_pairs_older_than_year()
    
    # Анализируем пары для сеточной торговли
    if old_pairs:
        # Для примера берем только 5 пар
        best_pairs = grid_analyzer.get_best_grid_pairs(old_pairs[:5])
        
        if not best_pairs.empty:
            print("\nЛучшие пары для сеточной торговли:")
            for _, row in best_pairs.iterrows():
                print(f"{row['symbol']}: доходность {row['potential_monthly_profit_pct']:.2f}%, "
                      f"риск: {row['risk_level_text']}, шаг: {row['recommended_step_pct']:.2f}%")
      # Тест приближённой симуляции двух сеток по всем парам
    print("\nТестирование двойных сеток:")
    for symbol in old_pairs[:5]:
        df = collector.get_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, 30)
        if not df.empty:
            dual_res = grid_analyzer.estimate_dual_grid_by_candles(df)
            print(f"{symbol}: комбинированная доходность: {dual_res['combined_pct']:.2f}%, "
                  f"long: {dual_res['long_pct']:.2f}%, short: {dual_res['short_pct']:.2f}%, "
                  f"выходов за пределы: {dual_res['breaks']}")
            
            # Дополнительно выведем первые несколько свечей для анализа
            print(f"Первые 3 свечи для {symbol}:")
            for i, (_, candle) in enumerate(df.iloc[:3].iterrows()):
                print(f"  {i+1}: Open: {candle['open']:.2f}, High: {candle['high']:.2f}, "
                      f"Low: {candle['low']:.2f}, Close: {candle['close']:.2f}, "
                      f"Range: {(candle['high']-candle['low'])/candle['low']*100:.2f}%")
