"""
Модуль сбора данных с Binance API.
Отвечает за получение данных о торговых парах, их истории и текущих ценах.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any

import pandas as pd
from binance.client import Client


class BinanceDataCollector:
    """
    Класс для сбора данных с Binance API.
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
        exchange_info = self.client.get_exchange_info()
        usdt_pairs = []
        
        for symbol_info in exchange_info['symbols']:
            symbol = symbol_info['symbol']
            # Проверяем, что пара активна и заканчивается на USDT
            if symbol.endswith('USDT') and symbol_info['status'] == 'TRADING':
                usdt_pairs.append(symbol)
                
        return usdt_pairs
        
    def get_pairs_older_than_year(self) -> List[str]:
        """
        Получение пар, которые существуют не менее 1 года.
        
        Returns:
            Список пар, существующих более года
        """
        all_pairs = self.get_all_usdt_pairs()
        one_year_ago = (datetime.now() - timedelta(days=365)).timestamp() * 1000
        valid_pairs = []
        
        print(f"Найдено {len(all_pairs)} торговых пар с USDT. Проверка возраста пар...")
        
        # Ограничиваем количество пар для проверки, чтобы не перегружать API
        max_pairs_to_check = 20
        if len(all_pairs) > max_pairs_to_check:
            print(f"Для экономии времени будет проверено только {max_pairs_to_check} пар")
            pairs_to_check = all_pairs[:max_pairs_to_check]
        else:
            pairs_to_check = all_pairs
        
        total_pairs = len(pairs_to_check)
        for i, pair in enumerate(pairs_to_check):
            try:
                if i % 2 == 0:  # Увеличиваем частоту сообщений
                    print(f"Проверка пары {i+1}/{total_pairs}: {pair}")
                
                # Получаем первую свечу для пары
                klines = self.client.get_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_1DAY,
                    limit=1,
                    startTime=0
                )
                
                if klines and float(klines[0][0]) < one_year_ago:
                    valid_pairs.append(pair)
                    print(f"Пара {pair} добавлена в список (старше 1 года)")
                else:
                    print(f"Пара {pair} не соответствует критерию возраста")
            except Exception as e:
                print(f"Ошибка при проверке пары {pair}: {e}")
                continue
        
        print(f"Проверка завершена. Найдено {len(valid_pairs)} пар старше 1 года")
        return valid_pairs
    
    def get_historical_data(self, symbol: str, interval: str, days: int) -> pd.DataFrame:
        """
        Получение исторических данных для указанной пары.
        
        Args:
            symbol: Символ торговой пары
            interval: Интервал данных (например, "1d" для дневных свечей)
            days: Количество дней для получения данных
            
        Returns:
            DataFrame с историческими данными
        """
        target_date = (datetime.now() - timedelta(days=days)).strftime("%d %b %Y %H:%M:%S")
        end_date = datetime.now().strftime("%d %b %Y %H:%M:%S")
        
        klines = self.client.get_historical_klines(
            symbol, interval, target_date, end_date, limit=1000
        )
        
        data = []
        for kline in klines:
            date = datetime.fromtimestamp(kline[0] / 1000)
            data.append({
                'date': date,
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                'close_time': datetime.fromtimestamp(kline[6] / 1000),
                'quote_asset_volume': float(kline[7]),
                'number_of_trades': int(kline[8]),
                'taker_buy_base_asset_volume': float(kline[9]),
                'taker_buy_quote_asset_volume': float(kline[10])
            })
        
        df = pd.DataFrame(data)
        if len(df) > 0:
            df.set_index('date', inplace=True)
        
        return df
    
    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Расчет дневной волатильности.
        
        Args:
            df: DataFrame с данными цен
            
        Returns:
            Средняя дневная волатильность в процентах
        """
        # Рассчитываем дневную волатильность как (high - low) / low * 100
        df['volatility'] = (df['high'] - df['low']) / df['low'] * 100
        
        return df['volatility'].mean()
    
    def check_sideways_range(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        Проверка, находится ли пара в боковике (в пределах 30%).
        
        Args:
            df: DataFrame с данными цен
            
        Returns:
            Кортеж (находится_в_боковике, процент_диапазона)
        """
        max_price = df['high'].max()
        min_price = df['low'].min()
        
        price_range_percent = (max_price - min_price) / min_price * 100
        
        return price_range_percent <= 30, price_range_percent
    
    def get_pair_stats(self, symbol: str, days: int = 365) -> Optional[Dict[str, Any]]:
        """
        Получение статистики по торговой паре.
        
        Args:
            symbol: Символ торговой пары
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой пары или None, если не удалось получить данные
        """
        try:
            df = self.get_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, days)
            
            if df.empty:
                return None
            
            volatility = self.calculate_volatility(df)
            is_sideways, range_percent = self.check_sideways_range(df)
            
            return {
                'symbol': symbol,
                'days_analyzed': days,
                'data_points': len(df),
                'current_price': df['close'].iloc[-1],
                'avg_daily_volatility': volatility,
                'is_sideways': is_sideways,
                'price_range_percent': range_percent,
                'first_date': df.index[0],
                'last_date': df.index[-1]
            }
        except Exception as e:
            print(f"Ошибка при получении статистики для {symbol}: {e}")
            return None
        
    def get_historical_klines(self, symbol: str, interval: str, start_str: str, end_str: Optional[str] = None) -> List[List[Any]]:
        """
        Получение исторических свечей для указанной пары.
        
        Args:
            symbol: Символ торговой пары
            interval: Интервал данных
            start_str: Начальное время (в миллисекундах или строка даты)
            end_str: Конечное время (в миллисекундах или строка даты)
            
        Returns:
            Список свечей в формате Binance
        """
        try:
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str,
                limit=1000
            )
            return klines
        except Exception as e:
            print(f"Ошибка при получении исторических данных для {symbol}: {e}")
            return []


if __name__ == "__main__":
    # Пример использования
    api_key = "YOUR_API_KEY"
    api_secret = "YOUR_API_SECRET"
    
    collector = BinanceDataCollector(api_key, api_secret)
    
    # Получаем пары старше 1 года
    old_pairs = collector.get_pairs_older_than_year()
    print(f"Найдено {len(old_pairs)} пар старше 1 года")
    
    # Собираем статистику по первым 5 парам
    for symbol in old_pairs[:5]:
        stats = collector.get_pair_stats(symbol)
        if stats:
            print(f"\nСтатистика для {symbol}:")
            print(f"Средняя дневная волатильность: {stats['avg_daily_volatility']:.2f}%")
            print(f"В боковике (<=30%): {stats['is_sideways']}")
            print(f"Процент диапазона цены: {stats['price_range_percent']:.2f}%")
