"""
Flask-адаптер для развертывания на Vercel
Конвертирует Streamlit функциональность в Flask API
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
from datetime import datetime
from typing import Dict, Any

# Импорты модулей проекта
from modules.collector import BinanceDataCollector
from modules.processor import DataProcessor
from modules.correlation import CorrelationAnalyzer
from modules.portfolio import PortfolioBuilder
from modules.grid_analyzer import GridAnalyzer
from modules.optimizer import GridOptimizer

app = Flask(__name__)

# Константы комиссий
MAKER_COMMISSION_RATE = 0.0002
TAKER_COMMISSION_RATE = 0.0005

# HTML шаблон для главной страницы
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализатор торговых пар Binance</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .results { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 4px; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #e9ecef; border: 1px solid #ddd; cursor: pointer; }
        .tab.active { background: #007bff; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .loading { display: none; text-align: center; padding: 20px; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .success { color: #155724; background: #d4edda; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Анализатор торговых пар Binance</h1>
            <p>Веб-версия для Vercel</p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('analysis')">📊 Анализ</div>
            <div class="tab" onclick="showTab('grid')">⚡ Grid Trading</div>
            <div class="tab" onclick="showTab('optimization')">🤖 Оптимизация</div>
        </div>

        <!-- Вкладка анализа -->
        <div id="analysis" class="tab-content active">
            <div class="card">
                <h3>Настройки API</h3>
                <div class="form-group">
                    <label>API Key:</label>
                    <input type="password" id="apiKey" placeholder="Введите ваш API ключ Binance">
                </div>
                <div class="form-group">
                    <label>API Secret:</label>
                    <input type="password" id="apiSecret" placeholder="Введите ваш секретный ключ">
                </div>
            </div>

            <div class="card">
                <h3>Параметры анализа</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Мин. объем торгов (USDT):</label>
                        <input type="number" id="minVolume" value="10000000" min="1000000">
                    </div>
                    <div class="form-group">
                        <label>Мин. цена (USDT):</label>
                        <input type="number" id="minPrice" value="0.01" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Макс. цена (USDT):</label>
                        <input type="number" id="maxPrice" value="100" step="10">
                    </div>
                    <div class="form-group">
                        <label>Количество пар:</label>
                        <input type="number" id="maxPairs" value="30" min="5" max="100">
                    </div>
                </div>
                <button class="btn" onclick="startAnalysis()">🚀 Запустить анализ</button>
            </div>

            <div id="analysisResults" class="results" style="display: none;">
                <h3>Результаты анализа</h3>
                <div id="analysisContent"></div>
            </div>
        </div>

        <!-- Вкладка Grid Trading -->
        <div id="grid" class="tab-content">
            <div class="card">
                <h3>Симуляция Grid Trading</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Торговая пара:</label>
                        <select id="gridPair">
                            <option value="BTCUSDT">BTCUSDT</option>
                            <option value="ETHUSDT">ETHUSDT</option>
                            <option value="BNBUSDT">BNBUSDT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Диапазон сетки (%):</label>
                        <input type="number" id="gridRange" value="20" min="5" max="50">
                    </div>
                    <div class="form-group">
                        <label>Шаг сетки (%):</label>
                        <input type="number" id="gridStep" value="1" min="0.1" max="5" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>Начальный баланс (USDT):</label>
                        <input type="number" id="gridBalance" value="1000" min="100">
                    </div>
                </div>
                <button class="btn" onclick="runGridSimulation()">⚡ Запустить симуляцию</button>
            </div>

            <div id="gridResults" class="results" style="display: none;">
                <h3>Результаты симуляции</h3>
                <div id="gridContent"></div>
            </div>
        </div>

        <!-- Вкладка оптимизации -->
        <div id="optimization" class="tab-content">
            <div class="card">
                <h3>Автоматическая оптимизация</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Пара для оптимизации:</label>
                        <select id="optPair">
                            <option value="BTCUSDT">BTCUSDT</option>
                            <option value="ETHUSDT">ETHUSDT</option>
                            <option value="BNBUSDT">BNBUSDT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Метод оптимизации:</label>
                        <select id="optMethod">
                            <option value="genetic">Генетический алгоритм</option>
                            <option value="adaptive">Адаптивный поиск</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Количество поколений:</label>
                        <input type="number" id="generations" value="10" min="5" max="20">
                    </div>
                    <div class="form-group">
                        <label>Размер популяции:</label>
                        <input type="number" id="population" value="20" min="10" max="50">
                    </div>
                </div>
                <button class="btn" onclick="runOptimization()">🤖 Запустить оптимизацию</button>
            </div>

            <div id="optimizationResults" class="results" style="display: none;">
                <h3>Результаты оптимизации</h3>
                <div id="optimizationContent"></div>
            </div>
        </div>

        <div class="loading" id="loading">
            <p>⏳ Обработка запроса...</p>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Скрыть все вкладки
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            
            // Показать выбранную вкладку
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }

        function showError(message) {
            hideLoading();
            alert('Ошибка: ' + message);
        }

        async function startAnalysis() {
            const apiKey = document.getElementById('apiKey').value;
            const apiSecret = document.getElementById('apiSecret').value;
            
            if (!apiKey || !apiSecret) {
                showError('Введите API ключи');
                return;
            }

            showLoading();

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        api_secret: apiSecret,
                        min_volume: parseInt(document.getElementById('minVolume').value),
                        min_price: parseFloat(document.getElementById('minPrice').value),
                        max_price: parseFloat(document.getElementById('maxPrice').value),
                        max_pairs: parseInt(document.getElementById('maxPairs').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('analysisResults').style.display = 'block';
                    document.getElementById('analysisContent').innerHTML = `
                        <div class="success">Анализ завершен успешно!</div>
                        <p>Найдено пар: ${data.pairs_count}</p>
                        <div>Топ пары: ${data.pairs.slice(0, 10).join(', ')}</div>
                    `;
                } else {
                    showError(data.error);
                }
            } catch (error) {
                showError('Ошибка сети: ' + error.message);
            }
            
            hideLoading();
        }

        async function runGridSimulation() {
            const apiKey = document.getElementById('apiKey').value;
            const apiSecret = document.getElementById('apiSecret').value;
            
            if (!apiKey || !apiSecret) {
                showError('Введите API ключи');
                return;
            }

            showLoading();

            try {
                const response = await fetch('/api/grid_simulation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        api_secret: apiSecret,
                        pair: document.getElementById('gridPair').value,
                        grid_range_pct: parseFloat(document.getElementById('gridRange').value),
                        grid_step_pct: parseFloat(document.getElementById('gridStep').value),
                        initial_balance: parseFloat(document.getElementById('gridBalance').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('gridResults').style.display = 'block';
                    document.getElementById('gridContent').innerHTML = `
                        <div class="success">Симуляция завершена!</div>
                        <div class="grid">
                            <div class="card">
                                <h4>Long позиция</h4>
                                <p>PnL: $${data.stats_long.total_pnl.toFixed(2)} (${data.stats_long.total_pnl_pct.toFixed(2)}%)</p>
                                <p>Сделок: ${data.stats_long.trades_count}</p>
                            </div>
                            <div class="card">
                                <h4>Short позиция</h4>
                                <p>PnL: $${data.stats_short.total_pnl.toFixed(2)} (${data.stats_short.total_pnl_pct.toFixed(2)}%)</p>
                                <p>Сделок: ${data.stats_short.trades_count}</p>
                            </div>
                        </div>
                    `;
                } else {
                    showError(data.error);
                }
            } catch (error) {
                showError('Ошибка сети: ' + error.message);
            }
            
            hideLoading();
        }

        async function runOptimization() {
            const apiKey = document.getElementById('apiKey').value;
            const apiSecret = document.getElementById('apiSecret').value;
            
            if (!apiKey || !apiSecret) {
                showError('Введите API ключи');
                return;
            }

            showLoading();

            try {
                const response = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: apiKey,
                        api_secret: apiSecret,
                        pair: document.getElementById('optPair').value,
                        method: document.getElementById('optMethod').value,
                        generations: parseInt(document.getElementById('generations').value),
                        population_size: parseInt(document.getElementById('population').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('optimizationResults').style.display = 'block';
                    const best = data.results[0];
                    document.getElementById('optimizationContent').innerHTML = `
                        <div class="success">Оптимизация завершена!</div>
                        <div class="card">
                            <h4>🥇 Лучший результат</h4>
                            <p>Комбинированный скор: ${best.combined_score.toFixed(2)}%</p>
                            <p>Диапазон сетки: ${best.params.grid_range_pct.toFixed(1)}%</p>
                            <p>Шаг сетки: ${best.params.grid_step_pct.toFixed(2)}%</p>
                            <p>Стоп-лосс: ${best.params.stop_loss_pct.toFixed(1)}%</p>
                            <p>Бэктест vs Форвард: ${best.backtest_score.toFixed(2)}% vs ${best.forward_score.toFixed(2)}%</p>
                        </div>
                    `;
                } else {
                    showError(data.error);
                }
            } catch (error) {
                showError('Ошибка сети: ' + error.message);
            }
            
            hideLoading();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Главная страница"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze_pairs():
    """API для анализа торговых пар"""
    try:
        data = request.json
        
        # Инициализация модулей
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        processor = DataProcessor(collector)
        
        # Получение и фильтрация пар
        all_pairs = collector.get_all_usdt_pairs()
        filtered_pairs = processor.filter_pairs_by_volume_and_price(
            all_pairs,
            min_volume=data['min_volume'],
            min_price=data['min_price'],
            max_price=data['max_price']
        )
        
        pairs_to_analyze = filtered_pairs[:data['max_pairs']]
        
        return jsonify({
            'success': True,
            'pairs_count': len(pairs_to_analyze),
            'pairs': pairs_to_analyze
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/grid_simulation', methods=['POST'])
def grid_simulation():
    """API для симуляции Grid Trading"""
    try:
        data = request.json
        
        # Инициализация
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        grid_analyzer = GridAnalyzer(collector)
        
        # Получение данных
        df = collector.get_historical_data(data['pair'], '1h', 1000)
        
        # Симуляция
        stats_long, stats_short, _, _ = grid_analyzer.estimate_dual_grid_by_candles_realistic(
            df=df,
            initial_balance_long=data['initial_balance'],
            initial_balance_short=data['initial_balance'],
            grid_range_pct=data['grid_range_pct'],
            grid_step_pct=data['grid_step_pct'],
            order_size_usd_long=0,
            order_size_usd_short=0,
            commission_pct=TAKER_COMMISSION_RATE * 100,
            debug=False
        )
        
        return jsonify({
            'success': True,
            'stats_long': stats_long,
            'stats_short': stats_short
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/optimize', methods=['POST'])
def optimize_parameters():
    """API для оптимизации параметров"""
    try:
        data = request.json
        
        # Инициализация
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        grid_analyzer = GridAnalyzer(collector)
        optimizer = GridOptimizer(grid_analyzer, TAKER_COMMISSION_RATE)
        
        # Получение данных
        df = collector.get_historical_data(data['pair'], '1h', 2000)
        
        # Оптимизация
        if data['method'] == 'genetic':
            results = optimizer.optimize_genetic(
                df=df,
                initial_balance=1000,
                population_size=data['population_size'],
                generations=data['generations'],
                max_workers=2  # Ограничиваем для Vercel
            )
        else:
            results = optimizer.grid_search_adaptive(
                df=df,
                initial_balance=1000,
                iterations=3,
                points_per_iteration=30
            )
        
        # Сериализация результатов
        serialized_results = []
        for result in results[:10]:  # Топ-10
            serialized_results.append({
                'combined_score': result.combined_score,
                'backtest_score': result.backtest_score,
                'forward_score': result.forward_score,
                'trades_count': result.trades_count,
                'drawdown': result.drawdown,
                'params': {
                    'grid_range_pct': result.params.grid_range_pct,
                    'grid_step_pct': result.params.grid_step_pct,
                    'stop_loss_pct': result.params.stop_loss_pct
                }
            })
        
        return jsonify({
            'success': True,
            'results': serialized_results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Для локального тестирования
if __name__ == '__main__':
    app.run(debug=True)

# Для Vercel
def handler(request):
    return app(request.environ, lambda status, headers: None)
