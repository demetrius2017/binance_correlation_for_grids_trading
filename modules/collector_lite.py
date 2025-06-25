"""
Упрощённый модуль сбора данных с Binance API для Vercel Lite версии.
Без pandas для соответствия лимиту 250MB.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from binance.client import Client


class BinanceDataCollector:
    """
    Упрощённый класс для сбора данных с Binance API.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Инициализация клиента Binance.
        
        Args:
            api_key: API ключ Binance
            api_secret: Секретный ключ API Binance
        """
        self.client = Client(api_key, api_secret)
        
    def get_all_usdt_pairs(self) -> List[str]:
        """
        Получение всех торговых пар с USDT.
        
        Returns:
            Список всех торговых пар с USDT
        """
        try:
            exchange_info = self.client.get_exchange_info()
            usdt_pairs = []
            
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                # Проверяем, что пара активна и заканчивается на USDT
                if symbol.endswith('USDT') and symbol_info['status'] == 'TRADING':
                    usdt_pairs.append(symbol)
                    
            return sorted(usdt_pairs)
        except Exception as e:
            print(f"Ошибка получения пар: {e}")
            return []
        
    def get_ticker_24hr(self, symbol: str) -> Dict[str, Any]:
        """
        Получение 24-часовой статистики для символа.
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Словарь с данными тикера
        """
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            return {
                'symbol': ticker['symbol'],
                'price': float(ticker['lastPrice']),
                'volume': float(ticker['volume']),
                'quote_volume': float(ticker['quoteVolume']),
                'price_change_pct': float(ticker['priceChangePercent']),
                'count': int(ticker['count'])
            }
        except Exception as e:
            print(f"Ошибка получения тикера для {symbol}: {e}")
            return {}
            
    def get_historical_data(self, symbol: str, interval: str, limit: int = 500) -> List[Dict]:
        """
        Получение исторических данных в виде списка словарей.
        
        Args:
            symbol: Торговая пара
            interval: Интервал (1h, 4h, 1d и т.д.)
            limit: Количество свечей
            
        Returns:
            Список словарей с данными свечей
        """
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            candles = []
            for kline in klines:
                candle = {
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': int(kline[6]),
                    'quote_volume': float(kline[7]),
                    'trades_count': int(kline[8])
                }
                candles.append(candle)
                
            return candles
        except Exception as e:
            print(f"Ошибка получения исторических данных для {symbol}: {e}")
            return []
            
    def get_current_price(self, symbol: str) -> float:
        """
        Получение текущей цены символа.
        
        Args:
            symbol: Торговая пара
            
        Returns:
            Текущая цена
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Ошибка получения цены для {symbol}: {e}")
            return 0.0
            
    def get_top_pairs_by_volume(self, limit: int = 50) -> List[Dict]:
        """
        Получение топ пар по объёму торгов.
        
        Args:
            limit: Количество пар
            
        Returns:
            Список словарей с данными пар
        """
        try:
            tickers = self.client.get_ticker()
            
            # Фильтруем только USDT пары и сортируем по объёму
            usdt_tickers = []
            for ticker in tickers:
                if ticker['symbol'].endswith('USDT'):
                    usdt_tickers.append({
                        'symbol': ticker['symbol'],
                        'volume': float(ticker['quoteVolume']),
                        'price': float(ticker['lastPrice']),
                        'change_pct': float(ticker['priceChangePercent'])
                    })
            
            # Сортируем по объёму и возвращаем топ
            usdt_tickers.sort(key=lambda x: x['volume'], reverse=True)
            return usdt_tickers[:limit]
            
        except Exception as e:
            print(f"Ошибка получения топ пар: {e}")
            return []
            
    def simple_volatility(self, data: List[Dict], window: int = 20) -> float:
        """
        Простой расчёт волатильности на основе исторических данных.
        
        Args:
            data: Список свечей
            window: Окно для расчёта
            
        Returns:
            Волатильность в процентах
        """
        if len(data) < window:
            return 0.0
            
        try:
            # Берём последние свечи
            recent_data = data[-window:]
            prices = [candle['close'] for candle in recent_data]
            
            # Расчёт процентных изменений
            returns = []
            for i in range(1, len(prices)):
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
            
            # Стандартное отклонение
            if len(returns) > 1:
                volatility = float(np.std(returns) * 100)  # В процентах
                return volatility
            else:
                return 0.0
                
        except Exception as e:
            print(f"Ошибка расчёта волатильности: {e}")
            return 0.0
