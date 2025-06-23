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
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем родительский каталог в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.collector import BinanceDataCollector

# Реальные комиссии Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02% (для лимитных ордеров)
TAKER_COMMISSION_RATE = 0.0005  # 0.05% (для рыночных ордеров)

# Базовый капитал для расчетов
INITIAL_CAPITAL = 1000.0  # $1000 базовый капитал


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
        
        # Добавляем отслеживание текущего капитала
        self.current_capital = INITIAL_CAPITAL
        self.total_long_capital = 0
        self.total_short_capital = 0
    
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
                                   use_real_commissions: bool = True) -> Dict[str, Any]:
        """
        Оценка потенциальной доходности сеточной стратегии на паре.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            symbol: Торговая пара
            grid_range_pct: Диапазон сетки в процентах (±range/2 от текущей цены)
            grid_step_pct: Шаг сетки в процентах
            use_real_commissions: Использовать ли реальные комиссии Binance
            
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
        
        # Потенциальная доходность с учетом реальных комиссий
        if use_real_commissions:
            # В среднем половина сделок - maker, половина - taker
            avg_commission_rate = (MAKER_COMMISSION_RATE + TAKER_COMMISSION_RATE) / 2
            commission_pct = avg_commission_rate * 100
        else:
            commission_pct = 0.1  # Старая логика
            
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
            'commission_pct': commission_pct,
            'price_spikes_count': spikes,
            'price_spikes_per_month': spikes_per_month,
            'liquidity_5pct': liquidity['total_volume_5pct'],
            'risk_level_text': risk_level_text,
            'attractiveness_text': attractiveness_text
        }
    
    def estimate_dual_grid_by_candles(self,
                                     df: pd.DataFrame,
                                     grid_range_pct: float = 20.0,
                                     grid_step_pct: float = 1.0,
                                     use_real_commissions: bool = True,
                                     stop_loss_pct: float = 5.0,
                                     stop_loss_coverage: float = 0.5,
                                     stop_loss_strategy: str = "independent",
                                     close_both_on_stop_loss: bool = False) -> Dict[str, Any]:
        """
        Улучшенная симуляция двойных сеток с учетом реальных комиссий, 
        молний, стоп-лоссов и покрытия убытков.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            grid_range_pct: Диапазон сетки в процентах
            grid_step_pct: Шаг сетки в процентах
            use_real_commissions: Использовать ли реальные комиссии Binance
            stop_loss_pct: Размер стоп-лосса в процентах
            stop_loss_coverage: Доля покрытия убытков между сетками (0.0-1.0)
            stop_loss_strategy: Стратегия стоп-лосса ("independent" или "close_both")
            close_both_on_stop_loss: Закрывать ли обе сетки при стоп-лоссе одной
            
        Returns:
            Словарь с подробными результатами симуляции
        """
        # Определяем комиссии
        if use_real_commissions:
            maker_commission = MAKER_COMMISSION_RATE * 100  # В процентах
            taker_commission = TAKER_COMMISSION_RATE * 100  # В процентах
        else:
            maker_commission = 0.05  # Старая логика
            taker_commission = 0.1   # Старая логика
        
        # Инициализация переменных
        total_long_pnl = 0.0
        total_short_pnl = 0.0
        lightning_count = 0
        stop_loss_count = 0
        daily_range_coverage = 0.0
        long_active = True
        short_active = True
        
        # Статистика по сделкам
        long_trades = 0
        short_trades = 0
        long_maker_trades = 0
        short_maker_trades = 0
        long_taker_trades = 0
        short_taker_trades = 0
          # Используем шаг сетки, заданный пользователем
        effective_grid_step = grid_step_pct
        
        print(f"Используемый шаг сетки: {effective_grid_step:.2f}%")
        print(f"Комиссии: Maker {maker_commission:.3f}%, Taker {taker_commission:.3f}%")
        
        for i, (_, row) in enumerate(df.iterrows()):
            open_p, high_p, low_p, close_p = row['open'], row['high'], row['low'], row['close']
            
            # Расчет дневного диапазона
            daily_range_pct = (high_p - low_p) / low_p * 100
            daily_range_coverage += min(daily_range_pct / effective_grid_step, grid_range_pct / effective_grid_step)            # Проверка на молнию (резкое движение > 15%)
            if daily_range_pct > 15.0:
                lightning_count += 1
                # ИСПРАВЛЕНИЕ: Молния влияет на весь капитал
                # Рассчитываем текущий общий капитал
                current_total_capital = 100 + total_long_pnl + total_short_pnl  # 100% - начальный капитал
                
                # Убыток от молнии = процент от текущего капитала
                lightning_loss_pct = min(daily_range_pct * 0.3, 10.0)  # 30% от размера движения, но не более 10%
                lightning_loss_amount = current_total_capital * (lightning_loss_pct / 100)
                
                # Распределяем убыток между активными сетками
                active_grids = (1 if long_active else 0) + (1 if short_active else 0)
                if active_grids > 0:
                    loss_per_grid = lightning_loss_amount / active_grids
                    if long_active:
                        total_long_pnl -= loss_per_grid
                    if short_active:
                        total_short_pnl -= loss_per_grid
                
                print(f"Молния в день {i+1}: диапазон {daily_range_pct:.2f}%")
                print(f"Текущий капитал: {current_total_capital:.2f}%, убыток от молнии: -{lightning_loss_amount:.2f}%")
                continue
            
            # Расчет компонентов свечи
            base_price = min(open_p, close_p)
            body_pct = abs(close_p - open_p) / base_price * 100
            upper_wick_pct = (high_p - max(open_p, close_p)) / base_price * 100
            lower_wick_pct = (min(open_p, close_p) - low_p) / base_price * 100
            
            # Определяем направление свечи
            is_red_candle = close_p < open_p
            is_green_candle = close_p > open_p
              # Расчет количества сделок в тенях (maker ордера)
            upper_wick_trades = int(upper_wick_pct / effective_grid_step)
            lower_wick_trades = int(lower_wick_pct / effective_grid_step)
            body_trades = int(body_pct / effective_grid_step)
            
            # ИСПРАВЛЕНИЕ: Добавляем коэффициент реализма 
            # Не все движения в тенях приводят к сделкам из-за ликвидности и проскальзывания
            wick_efficiency = 0.75  # 75% эффективность исполнения ордеров
            
            # Обработка сделок Long сетки (если активна)
            if long_active:
                # Профит от теней (maker ордера) с коэффициентом реализма
                effective_wick_trades = (upper_wick_trades + lower_wick_trades) * wick_efficiency
                long_wick_profit = effective_wick_trades * (effective_grid_step - maker_commission)
                  # Расчет текущего капитала до стоп-лосса
                current_capital = self._calculate_current_capital("both")
                
                # Проверяем стоп-лосс
                if is_red_candle and body_pct > stop_loss_pct:
                    stop_loss_count += 1
                    
                    # Рассчитываем текущий капитал и убыток
                    current_total_capital = self._calculate_current_capital("both")
                    loss_amount = self._calculate_stop_loss_impact(body_pct, current_total_capital)
                    
                    # Обновляем капитал после стоп-лосса
                    if stop_loss_strategy == "independent":
                        # При независимой стратегии убыток только по Long позиции
                        self._update_capital_after_stop_loss(loss_amount, "long")
                        total_long_pnl -= loss_amount
                    else:
                        # При стратегии close_both убыток распределяется на обе позиции
                        self._update_capital_after_stop_loss(loss_amount, "both")
                        total_long_pnl -= loss_amount / 2
                        total_short_pnl -= loss_amount / 2
                        
                    print(f"Сработал стоп-лосс (Long): Текущий капитал: {current_total_capital:.2f}, убыток: -{loss_amount:.2f}")
                else:
                    # Обычная торговля без стоп-лосса
                    long_body_loss = 0
                    if is_red_candle and body_trades > 0:
                        long_body_loss = body_trades * taker_commission
                    
                    long_daily_pnl = long_wick_profit - long_body_loss
                    total_long_pnl += long_daily_pnl
                
                # Подсчет сделок (фактических)
                long_maker_trades += effective_wick_trades
                if is_red_candle and body_trades > 0:
                    long_taker_trades += body_trades                # Проверка стоп-лосса Long сетки
                if is_red_candle and body_pct > stop_loss_pct:
                    stop_loss_count += 1
                    # ИСПРАВЛЕНИЕ: Стоп-лосс влияет на весь капитал
                    # Рассчитываем текущий общий капитал (начальный + накопленная прибыль)
                    current_total_capital = 100 + total_long_pnl + total_short_pnl  # 100% - начальный капитал
                    
                    # Убыток от стоп-лосса = процент падения от текущего капитала
                    stop_loss_amount = current_total_capital * (body_pct / 100)
                    
                    # Вычитаем убыток из общего капитала (пропорционально между сетками)
                    long_loss = stop_loss_amount * 0.5  # 50% убытка на Long сетку
                    short_loss = stop_loss_amount * 0.5  # 50% убытка на Short сетку
                    
                    total_long_pnl -= long_loss
                    total_short_pnl -= short_loss
                    
                    print(f"Стоп-лосс Long сетки в день {i+1}: падение {body_pct:.2f}%")
                    print(f"Текущий капитал: {current_total_capital:.2f}%, убыток: -{stop_loss_amount:.2f}%")
                    print(f"Потери: Long -{long_loss:.2f}%, Short -{short_loss:.2f}%")
                    
                    if stop_loss_strategy == "close_both" or close_both_on_stop_loss:
                        long_active = False
                        short_active = False
                        print("Обе сетки закрыты по стоп-лоссу")
                        break
                    else:
                        print(f"Long сетка продолжает работу после стоп-лосса")
              # Обработка сделок Short сетки (если активна)
            if short_active:
                # Профит от теней (maker ордера) с коэффициентом реализма
                effective_wick_trades = (upper_wick_trades + lower_wick_trades) * wick_efficiency
                short_wick_profit = effective_wick_trades * (effective_grid_step - maker_commission)
                
                # Убыток от тела при росте (taker ордера при стоп-лоссе)
                short_body_loss = 0
                if is_green_candle and body_trades > 0:
                    short_body_loss = body_trades * taker_commission  # Только комиссия, убыток покрывается
                
                short_daily_pnl = short_wick_profit - short_body_loss
                total_short_pnl += short_daily_pnl
                
                # Подсчет сделок (фактических)
                short_maker_trades += effective_wick_trades
                if is_green_candle and body_trades > 0:
                    short_taker_trades += body_trades                # Проверка стоп-лосса Short сетки
                if is_green_candle and body_pct > stop_loss_pct:
                    stop_loss_count += 1
                    # ИСПРАВЛЕНИЕ: Стоп-лосс влияет на весь капитал
                    # Рассчитываем текущий общий капитал (начальный + накопленная прибыль)
                    current_total_capital = 100 + total_long_pnl + total_short_pnl  # 100% - начальный капитал
                    
                    # Убыток от стоп-лосса = процент роста от текущего капитала
                    stop_loss_amount = current_total_capital * (body_pct / 100)
                    
                    # Вычитаем убыток из общего капитала (пропорционально между сетками)
                    long_loss = stop_loss_amount * 0.5  # 50% убытка на Long сетку
                    short_loss = stop_loss_amount * 0.5  # 50% убытка на Short сетку
                    
                    total_long_pnl -= long_loss
                    total_short_pnl -= short_loss
                    
                    print(f"Стоп-лосс Short сетки в день {i+1}: рост {body_pct:.2f}%")
                    print(f"Текущий капитал: {current_total_capital:.2f}%, убыток: -{stop_loss_amount:.2f}%")
                    print(f"Потери: Long -{long_loss:.2f}%, Short -{short_loss:.2f}%")
                    
                    if stop_loss_strategy == "close_both" or close_both_on_stop_loss:
                        long_active = False
                        short_active = False
                        print("Обе сетки закрыты по стоп-лоссу")
                        break
                    else:
                        print(f"Short сетка продолжает работу после стоп-лосса")
            
            # Если обе сетки неактивны, прерываем симуляцию
            if not long_active and not short_active:
                break
        
        # Расчет итоговых метрик
        total_trades = long_maker_trades + long_taker_trades + short_maker_trades + short_taker_trades
        combined_pnl = total_long_pnl + total_short_pnl
        
        # Среднее покрытие дневных колебаний
        avg_daily_coverage = daily_range_coverage / len(df) if len(df) > 0 else 0
        
        return {
            'combined_pct': combined_pnl,
            'long_pct': total_long_pnl,
            'short_pct': total_short_pnl,
            'lightning_count': lightning_count,
            'stop_loss_count': stop_loss_count,
            'long_active': long_active,
            'short_active': short_active,
            'strategy': stop_loss_strategy,
            'grid_step_pct': effective_grid_step,
            'avg_daily_coverage_pct': avg_daily_coverage,
            'total_trades': total_trades,
            'long_maker_trades': long_maker_trades,
            'long_taker_trades': long_taker_trades,
            'short_maker_trades': short_maker_trades,
            'short_taker_trades': short_taker_trades,
            'maker_commission_pct': maker_commission,
            'taker_commission_pct': taker_commission,
            'stop_loss_pct': stop_loss_pct,
            'stop_loss_coverage': stop_loss_coverage
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

    def _calculate_current_capital(self, position_type: str = "both") -> float:
        """
        Расчет текущего капитала с учетом типа позиции.
        
        Args:
            position_type: Тип позиции ("long", "short" или "both")
            
        Returns:
            Текущий капитал в долларах
        """
        if position_type == "long":
            return self.total_long_capital
        elif position_type == "short":
            return self.total_short_capital
        else:
            return self.total_long_capital + self.total_short_capital
    
    def _calculate_stop_loss_impact(self, price_change_pct: float, current_capital: float) -> float:
        """
        Расчет влияния стоп-лосса на капитал.
        
        Args:
            price_change_pct: Процентное изменение цены
            current_capital: Текущий капитал
            
        Returns:
            Убыток в процентах от текущего капитала
        """
        # Убыток считается как процент от текущего капитала
        loss_amount = current_capital * (price_change_pct / 100)
        return loss_amount
    
    def _update_capital_after_stop_loss(self, loss_amount: float, position_type: str = "both") -> None:
        """
        Обновление капитала после срабатывания стоп-лосса.
        
        Args:
            loss_amount: Сумма убытка
            position_type: Тип позиции ("long", "short" или "both")
        """
        if position_type in ["both", "long"]:
            self.total_long_capital = max(0, self.total_long_capital - loss_amount / 2)
        if position_type in ["both", "short"]:
            self.total_short_capital = max(0, self.total_short_capital - loss_amount / 2)
        
        # Обновляем общий капитал
        self.current_capital = self.total_long_capital + self.total_short_capital

    def analyze_pair(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализирует торговую пару и возвращает ее характеристики.
        
        Args:
            df: DataFrame с историческими данными (OHLC)
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            # Базовые метрики
            latest_close = df['close'].iloc[-1]
            volume_24h = df['volume'].iloc[-1]
            
            # Расчет волатильности (ATR)
            volatility = self.calculate_atr(df)
            
            # Диапазон цены
            price_range = (df['high'].max() - df['low'].min()) / df['low'].min() * 100
            
            # Проверка на боковое движение
            is_sideways = self._is_sideways_market(df)
            
            # Подсчет резких движений
            spikes = self.count_price_spikes(df)
            
            # Оценка ликвидности
            liquidity_score = self._calculate_liquidity_score(volume_24h, latest_close)
            
            # Итоговый рейтинг
            total_score = self._calculate_total_score(
                volatility=volatility,
                price_range=price_range,
                is_sideways=is_sideways,
                spikes=spikes,
                liquidity=liquidity_score
            )
            
            return {
                'volatility': volatility,
                'volume_24h': volume_24h,
                'price_range_percent': price_range,
                'is_sideways': is_sideways,
                'lightning_count': spikes,
                'liquidity_score': liquidity_score,
                'total_score': total_score
            }
        except Exception as e:
            print(f"Ошибка при анализе пары: {str(e)}")
            return {}
            
    def _is_sideways_market(self, df: pd.DataFrame, threshold: float = 5.0) -> bool:
        """
        Определяет, находится ли рынок в боковом движении.
        
        Args:
            df: DataFrame с историческими данными
            threshold: Порог изменения цены в процентах
            
        Returns:
            True если рынок в боковике, False иначе
        """
        # Расчет общего тренда
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        total_change = abs((end_price - start_price) / start_price * 100)
        
        return total_change <= threshold
            
    def _calculate_liquidity_score(self, volume_24h: float, price: float) -> float:
        """
        Рассчитывает оценку ликвидности на основе объема торгов.
        
        Args:
            volume_24h: Объем торгов за 24 часа в USDT
            price: Текущая цена актива
            
        Returns:
            Оценка ликвидности от 0 до 1
        """
        # Объем в USDT
        volume_usdt = volume_24h * price
        
        # Базовые пороги
        min_volume = 1_000_000  # $1M
        max_volume = 100_000_000  # $100M
        
        if volume_usdt <= min_volume:
            return 0.0
        elif volume_usdt >= max_volume:
            return 1.0
        else:
            # Логарифмическая шкала для оценки
            score = (np.log10(volume_usdt) - np.log10(min_volume)) / (np.log10(max_volume) - np.log10(min_volume))
            return min(max(score, 0.0), 1.0)
            
    def _calculate_total_score(self,
                             volatility: float,
                             price_range: float,
                             is_sideways: bool,
                             spikes: int,
                             liquidity: float) -> float:
        """
        Рассчитывает итоговый рейтинг пары для сеточной торговли.
        
        Args:
            volatility: Значение ATR в процентах
            price_range: Диапазон цены в процентах
            is_sideways: Находится ли рынок в боковике
            spikes: Количество резких движений
            liquidity: Оценка ликвидности (0-1)
            
        Returns:
            Итоговый рейтинг от 0 до 1
        """
        # Веса для разных факторов
        weights = {
            'volatility': 0.3,
            'sideways': 0.2,
            'spikes': -0.2,  # Негативный вес для резких движений
            'liquidity': 0.3
        }
        
        # Нормализация значений
        volatility_score = min(volatility / 10.0, 1.0)  # Оптимально 5-10% ATR
        spikes_score = max(0, 1 - (spikes / 10.0))  # Меньше резких движений лучше
        
        # Расчет итогового рейтинга
        score = (
            weights['volatility'] * volatility_score +
            weights['sideways'] * float(is_sideways) +
            weights['spikes'] * spikes_score +
            weights['liquidity'] * liquidity
        )
        
        return max(min(score, 1.0), 0.0)

    def _apply_commission(self, amount: float, is_maker: bool = True) -> float:
        """
        Применяет комиссию Binance к сумме сделки.
        
        Args:
            amount: Сумма сделки
            is_maker: True если это лимитный ордер, False если маркет
            
        Returns:
            Сумма с учетом комиссии
        """
        commission = MAKER_COMMISSION_RATE if is_maker else TAKER_COMMISSION_RATE
        return amount * (1 - commission)



if __name__ == "__main__":
    # Пример использования с новой логикой комиссий
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
    
    # Тестирование симуляции с реальными комиссиями
    if old_pairs:
        print("\nТестирование двойных сеток с реальными комиссиями Binance:")
        for symbol in old_pairs[:3]:  # Тестируем на 3 парах
            df = collector.get_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, 30)
            if not df.empty:
                # Симуляция с реальными комиссиями
                real_result = grid_analyzer.estimate_dual_grid_by_candles(
                    df, use_real_commissions=True, stop_loss_pct=5.0
                )
                
                # Симуляция со старой логикой для сравнения
                old_result = grid_analyzer.estimate_dual_grid_by_candles(
                    df, use_real_commissions=False, stop_loss_pct=5.0
                )
                
                print(f"\n{symbol}:")
                print(f"  С реальными комиссиями: {real_result['combined_pct']:.2f}% "
                      f"(Long: {real_result['long_pct']:.2f}%, Short: {real_result['short_pct']:.2f}%)")
                print(f"  Со старой логикой: {old_result['combined_pct']:.2f}% "
                      f"(Long: {old_result['long_pct']:.2f}%, Short: {old_result['short_pct']:.2f}%)")
                print(f"  Разница: {real_result['combined_pct'] - old_result['combined_pct']:.2f}%")
                print(f"  Всего сделок: {real_result['total_trades']}, Молний: {real_result['lightning_count']}")
    
    # Пример анализа пары с новым методом
    if old_pairs:
        print("\nАнализ пар с новым методом:")
        for symbol in old_pairs[:3]:
            df = collector.get_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, 30)
            if not df.empty:
                analysis = grid_analyzer.analyze_pair(df)
                print(f"{symbol}: {analysis['total_score']:.2f} (Волатильность: {analysis['volatility']:.2f}%, "
                      f"Диапазон цены: {analysis['price_range_percent']:.2f}%, "
                      f"Ликвидность: {analysis['liquidity_score']:.2f}, "
                      f"Резкие движения: {analysis['lightning_count']})")
