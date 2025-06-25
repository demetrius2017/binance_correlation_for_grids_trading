"""
Полнофункциональная Flask API для Vercel Pro с Grid Trading и оптимизацией
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Импорты модулей проекта
from modules.collector import BinanceDataCollector
from modules.grid_analyzer import GridAnalyzer
from modules.optimizer import GridOptimizer, OptimizationParams

app = Flask(__name__)

# Константы комиссий Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02%
TAKER_COMMISSION_RATE = 0.0005  # 0.05%

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

# HTML шаблон с полной функциональностью
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анализатор торговых пар Binance - Full</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            padding: 20px;
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 {
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3em;
            margin-bottom: 10px;
        }
        .tabs { 
            display: flex; 
            margin-bottom: 20px; 
            background: white;
            border-radius: 15px;
            padding: 5px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .tab { 
            flex: 1;
            padding: 15px 25px; 
            background: transparent; 
            border: none;
            cursor: pointer; 
            font-size: 16px;
            font-weight: bold;
            border-radius: 10px;
            transition: all 0.3s;
            text-align: center;
        }
        .tab:hover { background: rgba(102, 126, 234, 0.1); }
        .tab.active { 
            background: linear-gradient(45deg, #667eea, #764ba2); 
            color: white; 
            transform: translateY(-2px);
        }
        .tab-content { 
            display: none; 
            animation: fadeIn 0.5s;
        }
        .tab-content.active { display: block; }
        .card { 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
        }
        .form-group { 
            margin-bottom: 20px; 
        }
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: bold; 
            color: #555;
        }
        .form-group input, .form-group select { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #ddd; 
            border-radius: 10px; 
            font-size: 16px;
            transition: all 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            border-color: #667eea;
            outline: none;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
        }
        .btn { 
            background: linear-gradient(45deg, #667eea, #764ba2); 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
            display: inline-block;
            text-decoration: none;
        }
        .btn:hover { 
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
        }
        .grid-2 { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
        }
        .results { 
            margin-top: 20px; 
            padding: 25px; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .loading { 
            display: none; 
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        .loading.show { display: flex; }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }
        .loading-text {
            color: white;
            font-size: 18px;
            text-align: center;
        }
        .error { 
            color: #dc3545; 
            background: #f8d7da; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 10px 0; 
            border-left: 4px solid #dc3545;
        }
        .success { 
            color: #155724; 
            background: #d4edda; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 10px 0; 
            border-left: 4px solid #28a745;
        }
        .warning {
            color: #856404;
            background: #fff3cd;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 4px solid #ffc107;
        }
        .metric {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .optimization-result {
            border: 2px solid #28a745;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        }
        .rank-badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Binance Grid Trading Pro</h1>
            <p>Полнофункциональная система анализа и оптимизации</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('grid')">⚡ Grid Trading</button>
            <button class="tab" onclick="showTab('optimization')">🤖 Авто-оптимизация</button>
            <button class="tab" onclick="showTab('analysis')">📊 Анализ пар</button>
            <button class="tab" onclick="showTab('settings')">⚙️ Настройки</button>
        </div>

        <!-- Вкладка Grid Trading -->
        <div id="grid" class="tab-content active">
            <div class="card">
                <h3>⚡ Симуляция Grid Trading</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Торговая пара:</label>
                        <select id="gridPair">
                            <option value="BTCUSDT">BTCUSDT</option>
                            <option value="ETHUSDT">ETHUSDT</option>
                            <option value="BNBUSDT">BNBUSDT</option>
                            <option value="ADAUSDT">ADAUSDT</option>
                            <option value="XRPUSDT">XRPUSDT</option>
                            <option value="LINKUSDT">LINKUSDT</option>
                            <option value="DOTUSDT">DOTUSDT</option>
                            <option value="UNIUSDT">UNIUSDT</option>
                            <option value="LTCUSDT">LTCUSDT</option>
                            <option value="SOLUSDT">SOLUSDT</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Диапазон сетки (%):</label>
                        <input type="number" id="gridRange" value="20" min="5" max="50" step="1">
                    </div>
                    <div class="form-group">
                        <label>Шаг сетки (%):</label>
                        <input type="number" id="gridStep" value="1.0" min="0.1" max="5" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>Начальный баланс (USDT):</label>
                        <input type="number" id="gridBalance" value="1000" min="100" max="100000" step="100">
                    </div>
                    <div class="form-group">
                        <label>Стоп-лосс (%):</label>
                        <input type="number" id="gridStopLoss" value="5" min="0" max="20" step="0.5">
                    </div>
                    <div class="form-group">
                        <label>Дней истории:</label>
                        <input type="number" id="gridDays" value="90" min="30" max="365" step="10">
                    </div>
                </div>
                <button class="btn" onclick="runGridSimulation()">⚡ Запустить симуляцию</button>
            </div>

            <div id="gridResults" class="results" style="display: none;">
                <h3>📈 Результаты симуляции</h3>
                <div id="gridContent"></div>
            </div>
        </div>

        <!-- Вкладка оптимизации -->
        <div id="optimization" class="tab-content">
            <div class="card">
                <h3>🤖 Автоматическая оптимизация параметров</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Пара для оптимизации:</label>
                        <select id="optPair">
                            <option value="BTCUSDT">BTCUSDT</option>
                            <option value="ETHUSDT">ETHUSDT</option>
                            <option value="BNBUSDT">BNBUSDT</option>
                            <option value="ADAUSDT">ADAUSDT</option>
                            <option value="XRPUSDT">XRPUSDT</option>
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
                        <label>Баланс для тестов (USDT):</label>
                        <input type="number" id="optBalance" value="1000" min="100" max="10000" step="100">
                    </div>
                    <div class="form-group">
                        <label>Дней истории:</label>
                        <input type="number" id="optDays" value="180" min="60" max="365" step="30">
                    </div>
                    <div class="form-group">
                        <label>Размер популяции:</label>
                        <input type="number" id="population" value="30" min="10" max="100" step="10">
                    </div>
                    <div class="form-group">
                        <label>Поколений/Итераций:</label>
                        <input type="number" id="generations" value="15" min="5" max="50" step="5">
                    </div>
                </div>
                <button class="btn" onclick="runOptimization()">🚀 Запустить оптимизацию</button>
            </div>

            <div id="optimizationResults" class="results" style="display: none;">
                <h3>🏆 Результаты оптимизации</h3>
                <div id="optimizationContent"></div>
            </div>
        </div>

        <!-- Остальные вкладки -->
        <div id="analysis" class="tab-content">
            <div class="card">
                <h3>📊 Анализ торговых пар</h3>
                <p>Базовый анализ пар по объему и волатильности</p>
                <div class="grid-2">
                    <div class="form-group">
                        <label>Мин. объем (USDT):</label>
                        <input type="number" id="minVolume" value="10000000" min="1000000">
                    </div>
                    <div class="form-group">
                        <label>Количество пар:</label>
                        <input type="number" id="maxPairs" value="30" min="5" max="100">
                    </div>
                </div>
                <button class="btn" onclick="analyzePairs()">📊 Анализировать</button>
            </div>
            <div id="analysisResults" class="results" style="display: none;">
                <div id="analysisContent"></div>
            </div>
        </div>

        <div id="settings" class="tab-content">
            <div class="card">
                <h3>🔑 API Настройки</h3>
                <div class="form-group">
                    <label>Binance API Key:</label>
                    <input type="password" id="apiKey" placeholder="Введите ваш API ключ">
                </div>
                <div class="form-group">
                    <label>Binance API Secret:</label>
                    <input type="password" id="apiSecret" placeholder="Введите секретный ключ">
                </div>
                <button class="btn" onclick="saveCredentials()">💾 Сохранить</button>
                
                <div style="margin-top: 30px;">
                    <h4>ℹ️ Информация о системе</h4>
                    <p><strong>Комиссии Binance:</strong></p>
                    <ul>
                        <li>Maker: 0.02%</li>
                        <li>Taker: 0.05%</li>
                    </ul>
                    <p><strong>Возможности:</strong></p>
                    <ul>
                        <li>✅ Полнофункциональная симуляция Grid Trading</li>
                        <li>✅ Генетический алгоритм оптимизации</li>
                        <li>✅ Адаптивный поиск параметров</li>
                        <li>✅ Бэктест + Форвард тестирование</li>
                        <li>✅ Учет реальных комиссий</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div class="loading-text" id="loadingText">Обработка запроса...</div>
    </div>

    <script>
        // Сохранение креденциалов в localStorage
        function saveCredentials() {
            const apiKey = document.getElementById('apiKey').value;
            const apiSecret = document.getElementById('apiSecret').value;
            
            if (apiKey && apiSecret) {
                localStorage.setItem('binance_api_key', apiKey);
                localStorage.setItem('binance_api_secret', apiSecret);
                showMessage('success', 'API ключи сохранены!');
            } else {
                showMessage('error', 'Введите оба ключа');
            }
        }

        // Загрузка креденциалов
        function loadCredentials() {
            const apiKey = localStorage.getItem('binance_api_key') || '';
            const apiSecret = localStorage.getItem('binance_api_secret') || '';
            
            document.getElementById('apiKey').value = apiKey;
            document.getElementById('apiSecret').value = apiSecret;
        }

        // Инициализация при загрузке
        window.onload = function() {
            loadCredentials();
        };

        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function showLoading(text = 'Обработка запроса...') {
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loading').classList.add('show');
        }

        function hideLoading() {
            document.getElementById('loading').classList.remove('show');
        }

        function showMessage(type, message) {
            hideLoading();
            const className = type === 'error' ? 'error' : 'success';
            const alertDiv = document.createElement('div');
            alertDiv.className = className;
            alertDiv.innerHTML = message;
            
            // Найти активную вкладку и показать сообщение
            const activeTab = document.querySelector('.tab-content.active');
            activeTab.insertBefore(alertDiv, activeTab.firstChild);
            
            // Удалить через 5 секунд
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 5000);
        }

        function getCredentials() {
            const apiKey = localStorage.getItem('binance_api_key') || '';
            const apiSecret = localStorage.getItem('binance_api_secret') || '';
            
            if (!apiKey || !apiSecret) {
                showMessage('error', 'Сначала введите API ключи во вкладке Настройки');
                return null;
            }
            
            return { apiKey, apiSecret };
        }

        async function runGridSimulation() {
            const creds = getCredentials();
            if (!creds) return;

            showLoading('Запуск симуляции Grid Trading...');

            try {
                const response = await fetch('/api/grid_simulation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: creds.apiKey,
                        api_secret: creds.apiSecret,
                        pair: document.getElementById('gridPair').value,
                        grid_range_pct: parseFloat(document.getElementById('gridRange').value),
                        grid_step_pct: parseFloat(document.getElementById('gridStep').value),
                        initial_balance: parseFloat(document.getElementById('gridBalance').value),
                        stop_loss_pct: parseFloat(document.getElementById('gridStopLoss').value),
                        days: parseInt(document.getElementById('gridDays').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('gridResults').style.display = 'block';
                    
                    const totalPnl = data.stats_long.total_pnl + data.stats_short.total_pnl;
                    const totalPnlPct = ((totalPnl / (data.initial_balance * 2)) * 100);
                    const totalTrades = data.stats_long.trades_count + data.stats_short.trades_count;
                    const totalCommission = data.stats_long.total_commission + data.stats_short.total_commission;
                    
                    document.getElementById('gridContent').innerHTML = `
                        <div class="success">✅ Симуляция завершена для ${data.pair}!</div>
                        
                        <div class="grid" style="margin: 20px 0;">
                            <div class="metric">
                                <div class="metric-value">${totalPnlPct.toFixed(2)}%</div>
                                <div class="metric-label">Общий доход</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">$${totalPnl.toFixed(2)}</div>
                                <div class="metric-label">PnL в USD</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${totalTrades}</div>
                                <div class="metric-label">Всего сделок</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">$${totalCommission.toFixed(2)}</div>
                                <div class="metric-label">Комиссии</div>
                            </div>
                        </div>

                        <div class="grid">
                            <div class="card">
                                <h4>📈 Long позиция</h4>
                                <p><strong>PnL:</strong> $${data.stats_long.total_pnl.toFixed(2)} (${data.stats_long.total_pnl_pct.toFixed(2)}%)</p>
                                <p><strong>Сделок:</strong> ${data.stats_long.trades_count}</p>
                                <p><strong>Комиссии:</strong> $${data.stats_long.total_commission.toFixed(2)}</p>
                                <p><strong>Финальный баланс:</strong> $${data.stats_long.final_balance.toFixed(2)}</p>
                            </div>
                            <div class="card">
                                <h4>📉 Short позиция</h4>
                                <p><strong>PnL:</strong> $${data.stats_short.total_pnl.toFixed(2)} (${data.stats_short.total_pnl_pct.toFixed(2)}%)</p>
                                <p><strong>Сделок:</strong> ${data.stats_short.trades_count}</p>
                                <p><strong>Комиссии:</strong> $${data.stats_short.total_commission.toFixed(2)}</p>
                                <p><strong>Финальный баланс:</strong> $${data.stats_short.final_balance.toFixed(2)}</p>
                            </div>
                        </div>
                    `;
                    
                    showMessage('success', `Симуляция завершена! Общий доход: ${totalPnlPct.toFixed(2)}%`);
                } else {
                    showMessage('error', data.error);
                }
            } catch (error) {
                showMessage('error', 'Ошибка сети: ' + error.message);
            }
            
            hideLoading();
        }

        async function runOptimization() {
            const creds = getCredentials();
            if (!creds) return;

            showLoading('Запуск автоматической оптимизации...');

            try {
                const response = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: creds.apiKey,
                        api_secret: creds.apiSecret,
                        pair: document.getElementById('optPair').value,
                        method: document.getElementById('optMethod').value,
                        initial_balance: parseFloat(document.getElementById('optBalance').value),
                        days: parseInt(document.getElementById('optDays').value),
                        population_size: parseInt(document.getElementById('population').value),
                        generations: parseInt(document.getElementById('generations').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('optimizationResults').style.display = 'block';
                    
                    let resultsHtml = `
                        <div class="success">✅ Оптимизация завершена для ${data.pair}!</div>
                        <p><strong>Найдено ${data.results.length} вариантов параметров</strong></p>
                    `;
                    
                    // Топ-5 результатов
                    resultsHtml += '<h4>🏆 Топ-5 лучших результатов:</h4>';
                    data.results.slice(0, 5).forEach((result, index) => {
                        const stability = Math.abs(result.backtest_score - result.forward_score);
                        const stabilityColor = stability < 5 ? '#28a745' : stability < 10 ? '#ffc107' : '#dc3545';
                        
                        resultsHtml += `
                            <div class="optimization-result">
                                <span class="rank-badge">#${index + 1}</span>
                                <strong>Комбинированный скор: ${result.combined_score.toFixed(2)}%</strong>
                                <div class="grid-2" style="margin-top: 10px;">
                                    <div>
                                        <strong>Параметры:</strong><br>
                                        • Диапазон: ${result.params.grid_range_pct.toFixed(1)}%<br>
                                        • Шаг: ${result.params.grid_step_pct.toFixed(2)}%<br>
                                        • Стоп-лосс: ${result.params.stop_loss_pct.toFixed(1)}%
                                    </div>
                                    <div>
                                        <strong>Результаты:</strong><br>
                                        • Бэктест: ${result.backtest_score.toFixed(2)}%<br>
                                        • Форвард: ${result.forward_score.toFixed(2)}%<br>
                                        • Сделок: ${result.trades_count}<br>
                                        • <span style="color: ${stabilityColor}">Стабильность: ${stability.toFixed(2)}%</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    // Лучший результат
                    const best = data.results[0];
                    resultsHtml += `
                        <div class="card" style="margin-top: 20px; border: 3px solid #28a745;">
                            <h4>🥇 Рекомендуемые параметры:</h4>
                            <div class="grid">
                                <div class="metric">
                                    <div class="metric-value">${best.params.grid_range_pct.toFixed(1)}%</div>
                                    <div class="metric-label">Диапазон сетки</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">${best.params.grid_step_pct.toFixed(2)}%</div>
                                    <div class="metric-label">Шаг сетки</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">${best.params.stop_loss_pct.toFixed(1)}%</div>
                                    <div class="metric-label">Стоп-лосс</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-value">${best.combined_score.toFixed(2)}%</div>
                                    <div class="metric-label">Ожидаемый доход</div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    document.getElementById('optimizationContent').innerHTML = resultsHtml;
                    showMessage('success', `Оптимизация завершена! Лучший результат: ${best.combined_score.toFixed(2)}%`);
                } else {
                    showMessage('error', data.error);
                }
            } catch (error) {
                showMessage('error', 'Ошибка сети: ' + error.message);
            }
            
            hideLoading();
        }

        async function analyzePairs() {
            const creds = getCredentials();
            if (!creds) return;

            showLoading('Анализ торговых пар...');

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: creds.apiKey,
                        api_secret: creds.apiSecret,
                        min_volume: parseInt(document.getElementById('minVolume').value),
                        max_pairs: parseInt(document.getElementById('maxPairs').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('analysisResults').style.display = 'block';
                    document.getElementById('analysisContent').innerHTML = `
                        <div class="success">✅ Анализ завершен! Найдено ${data.pairs_count} пар</div>
                        <div class="card">
                            <h4>📋 Топ торговые пары:</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 15px;">
                                ${data.pairs.slice(0, 20).map((pair, index) => 
                                    `<div style="background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;">
                                        <span style="color: #667eea;">#${index + 1}</span><br>${pair}
                                    </div>`
                                ).join('')}
                            </div>
                        </div>
                    `;
                    showMessage('success', `Найдено ${data.pairs_count} подходящих пар`);
                } else {
                    showMessage('error', data.error);
                }
            } catch (error) {
                showMessage('error', 'Ошибка сети: ' + error.message);
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
