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
from modules.processor import DataProcessor
from modules.correlation import CorrelationAnalyzer
from modules.portfolio import PortfolioBuilder
from modules.grid_analyzer import GridAnalyzer
from modules.optimizer import GridOptimizer, OptimizationParams

app = Flask(__name__)

# Константы комиссий Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02%
TAKER_COMMISSION_RATE = 0.0005  # 0.05%

def get_request_data(required_keys: List[str]) -> Dict[str, Any]:
    """Безопасное получение данных из request.json с проверкой обязательных ключей"""
    if request.json is None:
        raise ValueError("Тело запроса должно содержать JSON данные")
    
    data = request.json
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Отсутствует обязательный параметр: {key}")
    
    return data

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
        .form-group input[type="range"] {
            padding: 8px;
            height: 40px;
            background: linear-gradient(to right, #667eea 0%, #667eea 50%, #ddd 50%, #ddd 100%);
            border-radius: 20px;
            outline: none;
            -webkit-appearance: none;
            appearance: none;
        }
        .form-group input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.5);
        }
        .form-group input[type="range"]::-moz-range-thumb {
            height: 20px;
            width: 20px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.5);
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
            <button class="tab active" onclick="showTab('settings')">⚙️ Настройки</button>
            <button class="tab" onclick="showTab('grid')">⚡ Grid Trading</button>
            <button class="tab" onclick="showTab('optimization')">🤖 Авто-оптимизация</button>
            <button class="tab" onclick="showTab('filter')">🔍 Фильтр торговых пар</button>
        </div>

        <!-- Вкладка Настройки (первая) -->
        <div id="settings" class="tab-content active">
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
                <button class="btn" onclick="saveCredentials()">� Сохранить API ключи</button>
            </div>

            <div class="card">
                <h3>🎯 Фильтр торговых пар</h3>
                <p>Настройте фильтры и загрузите актуальный список пар</p>
                <div class="grid">
                    <div class="form-group">
                        <label>Мин. объем (USDT):</label>
                        <input type="range" id="minVolumeSlider" min="1000000" max="100000000" step="1000000" value="10000000" oninput="updateSliderValue('minVolumeSlider', 'minVolumeValue')">
                        <span id="minVolumeValue">10,000,000</span> USDT
                    </div>
                    <div class="form-group">
                        <label>Мин. цена ($):</label>
                        <input type="range" id="minPriceSlider" min="0.001" max="10" step="0.001" value="0.001" oninput="updateSliderValue('minPriceSlider', 'minPriceValue')">
                        <span id="minPriceValue">0.001</span> $
                    </div>
                    <div class="form-group">
                        <label>Макс. цена ($):</label>
                        <input type="range" id="maxPriceSlider" min="1" max="100000" step="1" value="1000" oninput="updateSliderValue('maxPriceSlider', 'maxPriceValue')">
                        <span id="maxPriceValue">1,000</span> $
                    </div>
                    <div class="form-group">
                        <label>Количество пар:</label>
                        <input type="range" id="maxPairsSlider" min="10" max="200" step="10" value="50" oninput="updateSliderValue('maxPairsSlider', 'maxPairsValue')">
                        <span id="maxPairsValue">50</span> пар
                    </div>
                </div>
                <button class="btn" onclick="loadTradingPairs()" id="loadPairsBtn">🔄 Загрузить торговые пары</button>
                
                <div id="pairsLoadStatus" style="margin-top: 15px;"></div>
                
                <div style="margin-top: 20px;">
                    <h4>📋 Загруженные пары (<span id="pairsCount">По умолчанию</span>):</h4>
                    <div id="loadedPairsList" style="max-height: 200px; overflow-y: auto; margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <div style="font-size: 0.9em; color: #666;">
                            Используются популярные пары по умолчанию. Нажмите "Загрузить торговые пары" для получения актуального списка.
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
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
                    <li>✅ Динамическая загрузка торговых пар</li>
                </ul>
            </div>
        </div>

        <!-- Вкладка Grid Trading -->
        <div id="grid" class="tab-content">
            <div class="card">
                <h3>⚡ Симуляция Grid Trading</h3>
                <div class="grid">
                    <div class="form-group">
                        <label>Торговая пара:</label>
                        <select id="gridPair">
                            <!-- Будет заполнено динамически -->
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Начальный баланс (USDT):</label>
                        <input type="range" id="gridBalanceSlider" min="100" max="100000" step="100" value="1000" oninput="updateSliderValue('gridBalanceSlider', 'gridBalanceValue')">
                        <span id="gridBalanceValue">1,000</span> USDT
                    </div>
                    <div class="form-group">
                        <label>Диапазон сетки (%):</label>
                        <input type="range" id="gridRangeSlider" min="5" max="50" step="0.5" value="20" oninput="updateSliderValue('gridRangeSlider', 'gridRangeValue')">
                        <span id="gridRangeValue">20.0</span>%
                    </div>
                    <div class="form-group">
                        <label>Шаг сетки (%):</label>
                        <input type="range" id="gridStepSlider" min="0.1" max="5" step="0.1" value="1.0" oninput="updateSliderValue('gridStepSlider', 'gridStepValue')">
                        <span id="gridStepValue">1.0</span>%
                    </div>
                    <div class="form-group">
                        <label>Стоп-лосс (%):</label>
                        <input type="range" id="gridStopLossSlider" min="0" max="20" step="0.5" value="5" oninput="updateSliderValue('gridStopLossSlider', 'gridStopLossValue')">
                        <span id="gridStopLossValue">5.0</span>%
                    </div>
                    <div class="form-group">
                        <label>Дней истории:</label>
                        <input type="range" id="gridDaysSlider" min="7" max="365" step="7" value="90" oninput="updateSliderValue('gridDaysSlider', 'gridDaysValue')">
                        <span id="gridDaysValue">90</span> дней
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
                            <!-- Будет заполнено динамически -->
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
                        <input type="range" id="optBalanceSlider" min="100" max="10000" step="100" value="1000" oninput="updateSliderValue('optBalanceSlider', 'optBalanceValue')">
                        <span id="optBalanceValue">1,000</span> USDT
                    </div>
                    <div class="form-group">
                        <label>Дней истории:</label>
                        <input type="range" id="optDaysSlider" min="60" max="365" step="30" value="180" oninput="updateSliderValue('optDaysSlider', 'optDaysValue')">
                        <span id="optDaysValue">180</span> дней
                    </div>
                    <div class="form-group">
                        <label>Размер популяции:</label>
                        <input type="range" id="populationSlider" min="10" max="100" step="10" value="30" oninput="updateSliderValue('populationSlider', 'populationValue')">
                        <span id="populationValue">30</span> особей
                    </div>
                    <div class="form-group">
                        <label>Поколений/Итераций:</label>
                        <input type="range" id="generationsSlider" min="5" max="50" step="5" value="15" oninput="updateSliderValue('generationsSlider', 'generationsValue')">
                        <span id="generationsValue">15</span> поколений
                    </div>
                </div>
                <button class="btn" onclick="runOptimization()">🚀 Запустить оптимизацию</button>
            </div>

            <div id="optimizationResults" class="results" style="display: none;">
                <h3>🏆 Результаты оптимизации</h3>
                <div id="optimizationContent"></div>
            </div>
        </div>

        <!-- Фильтр торговых пар (упрощенный) -->
        <div id="filter" class="tab-content">
            <div class="card">
                <h3>� Фильтр торговых пар</h3>
                <p>Просмотр и тестирование фильтров торговых пар</p>
                
                <div id="filterResults" class="results">
                    <div id="filterContent">
                        <div class="warning">
                            ℹ️ Сначала загрузите торговые пары во вкладке "Настройки"
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="settings_old" class="tab-content" style="display: none;">
            <!-- Старая вкладка настроек, теперь не используется -->
        </div>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div class="loading-text" id="loadingText">Обработка запроса...</div>
    </div>

    <script>
        // Глобальные переменные
        let loadedTradingPairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT',
            'UNIUSDT', 'LTCUSDT', 'ATOMUSDT', 'NEARUSDT', 'FILUSDT'
        ]; // Популярные пары по умолчанию

        // Функция для обновления значений ползунков
        function updateSliderValue(sliderId, valueId) {
            const slider = document.getElementById(sliderId);
            const valueSpan = document.getElementById(valueId);
            let value = parseFloat(slider.value);
            
            // Форматирование в зависимости от типа значения
            if (sliderId.includes('Volume')) {
                valueSpan.textContent = (value / 1000000).toFixed(1) + 'M';
            } else if (sliderId.includes('Balance')) {
                valueSpan.textContent = value.toLocaleString();
            } else if (sliderId.includes('Price')) {
                valueSpan.textContent = value.toFixed(3);
            } else if (sliderId.includes('Pairs')) {
                valueSpan.textContent = value;
            } else {
                valueSpan.textContent = value.toFixed(1);
            }
            
            // Обновление цвета ползунка
            updateSliderBackground(slider);
        }

        // Обновление фона ползунка
        function updateSliderBackground(slider) {
            const min = slider.min;
            const max = slider.max;
            const val = slider.value;
            const percentage = ((val - min) / (max - min)) * 100;
            slider.style.background = `linear-gradient(to right, #667eea 0%, #667eea ${percentage}%, #ddd ${percentage}%, #ddd 100%)`;
        }

        // Инициализация ползунков
        function initializeSliders() {
            const sliders = document.querySelectorAll('input[type="range"]');
            sliders.forEach(slider => {
                const valueId = slider.id.replace('Slider', 'Value');
                updateSliderValue(slider.id, valueId);
            });
        }

        // Заполнение выпадающих списков торговых пар
        function populatePairSelects() {
            const gridSelect = document.getElementById('gridPair');
            const optSelect = document.getElementById('optPair');
            
            // Очистка списков
            gridSelect.innerHTML = '';
            optSelect.innerHTML = '';
            
            // Заполнение
            loadedTradingPairs.forEach(pair => {
                const gridOption = new Option(pair, pair);
                const optOption = new Option(pair, pair);
                gridSelect.add(gridOption);
                optSelect.add(optOption);
            });
            
            updatePairsDisplay();
        }

        // Обновление отображения загруженных пар
        function updatePairsDisplay() {
            const pairsCount = document.getElementById('pairsCount');
            const pairsList = document.getElementById('loadedPairsList');
            
            pairsCount.textContent = loadedTradingPairs.length;
            
            pairsList.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 5px;">
                    ${loadedTradingPairs.map((pair, index) => 
                        `<div style="background: ${index < 10 ? '#e8f5e8' : '#f0f0f0'}; padding: 5px; border-radius: 4px; text-align: center; font-size: 0.8em; font-weight: bold;">
                            ${pair}
                        </div>`
                    ).join('')}
                </div>
            `;
        }

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

        // Загрузка торговых пар с Binance
        async function loadTradingPairs() {
            const creds = getCredentials();
            if (!creds) return;

            const btn = document.getElementById('loadPairsBtn');
            const status = document.getElementById('pairsLoadStatus');
            
            btn.disabled = true;
            btn.textContent = '🔄 Загрузка...';
            status.innerHTML = '<div class="warning">⏳ Загрузка актуального списка торговых пар...</div>';

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        api_key: creds.apiKey,
                        api_secret: creds.apiSecret,
                        min_volume: parseInt(document.getElementById('minVolumeSlider').value),
                        min_price: parseFloat(document.getElementById('minPriceSlider').value),
                        max_price: parseFloat(document.getElementById('maxPriceSlider').value),
                        max_pairs: parseInt(document.getElementById('maxPairsSlider').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    loadedTradingPairs = data.pairs;
                    populatePairSelects();
                    
                    status.innerHTML = `
                        <div class="success">✅ Загружено ${data.pairs_count} торговых пар из ${data.total_pairs} доступных</div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            Фильтры: объем ≥ ${(document.getElementById('minVolumeSlider').value / 1000000).toFixed(1)}M USDT, 
                            цена ${document.getElementById('minPriceSlider').value}$ - ${document.getElementById('maxPriceSlider').value}$
                        </div>
                    `;
                    
                    // Обновляем фильтр
                    updateFilterDisplay();
                    
                    showMessage('success', `Загружен актуальный список из ${data.pairs_count} торговых пар`);
                } else {
                    status.innerHTML = `<div class="error">❌ Ошибка: ${data.error}</div>`;
                    showMessage('error', data.error);
                }
            } catch (error) {
                status.innerHTML = `<div class="error">❌ Ошибка сети: ${error.message}</div>`;
                showMessage('error', 'Ошибка сети: ' + error.message);
            }
            
            btn.disabled = false;
            btn.textContent = '🔄 Загрузить торговые пары';
        }

        // Обновление отображения фильтра
        function updateFilterDisplay() {
            const filterContent = document.getElementById('filterContent');
            
            if (loadedTradingPairs.length === 0) {
                filterContent.innerHTML = '<div class="warning">ℹ️ Сначала загрузите торговые пары во вкладке "Настройки"</div>';
                return;
            }
            
            filterContent.innerHTML = `
                <div class="success">✅ Доступно ${loadedTradingPairs.length} торговых пар</div>
                
                <div class="grid" style="margin: 20px 0;">
                    <div class="metric">
                        <div class="metric-value">${loadedTradingPairs.length}</div>
                        <div class="metric-label">Торговых пар</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${Math.min(10, loadedTradingPairs.length)}</div>
                        <div class="metric-label">Топ пары</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${(document.getElementById('minVolumeSlider').value / 1000000).toFixed(1)}M</div>
                        <div class="metric-label">Мин. объем USDT</div>
                    </div>
                </div>
                
                <div class="card">
                    <h4>🏆 Загруженные торговые пары:</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-top: 15px;">
                        ${loadedTradingPairs.map((pair, index) => 
                            `<div style="background: ${index < 10 ? '#e8f5e8' : '#f8f9fa'}; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; border: ${index < 10 ? '2px solid #28a745' : '1px solid #dee2e6'};">
                                <span style="color: ${index < 10 ? '#28a745' : '#667eea'};">#${index + 1}</span><br>
                                <span style="font-size: 0.9em;">${pair}</span>
                            </div>`
                        ).join('')}
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
                        <strong>💡 Совет:</strong> Пары в топ-10 (зеленые) имеют наивысший объем торгов и подходят для Grid Trading
                    </div>
                </div>
            `;
        }

        // Инициализация при загрузке
        window.onload = function() {
            loadCredentials();
            initializeSliders();
            populatePairSelects();
            updateFilterDisplay();
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
                        grid_range_pct: parseFloat(document.getElementById('gridRangeSlider').value),
                        grid_step_pct: parseFloat(document.getElementById('gridStepSlider').value),
                        initial_balance: parseFloat(document.getElementById('gridBalanceSlider').value),
                        stop_loss_pct: parseFloat(document.getElementById('gridStopLossSlider').value),
                        days: parseInt(document.getElementById('gridDaysSlider').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('gridResults').style.display = 'block';
                    
                    const totalPnl = data.stats_long.total_pnl + data.stats_short.total_pnl;
                    const totalPnlPct = ((totalPnl / (parseFloat(document.getElementById('gridBalanceSlider').value) * 2)) * 100);
                    const totalTrades = data.stats_long.trades_count + data.stats_short.trades_count;
                    const totalCommission = data.stats_long.total_commission + data.stats_short.total_commission;
                    
                    document.getElementById('gridContent').innerHTML = `
                        <div class="success">✅ Симуляция завершена для ${document.getElementById('gridPair').value}!</div>
                        
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
                        initial_balance: parseFloat(document.getElementById('optBalanceSlider').value),
                        days: parseInt(document.getElementById('optDaysSlider').value),
                        population_size: parseInt(document.getElementById('populationSlider').value),
                        generations: parseInt(document.getElementById('generationsSlider').value)
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('optimizationResults').style.display = 'block';
                    
                    let resultsHtml = `
                        <div class="success">✅ Оптимизация завершена для ${document.getElementById('optPair').value}!</div>
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
        data = get_request_data(['api_key', 'api_secret', 'min_volume', 'max_pairs'])
        
        # Опциональные параметры с значениями по умолчанию
        min_price = data.get('min_price', 0.001)  # Минимум $0.001
        max_price = data.get('max_price', 100000.0)  # Максимум $100,000
        
        # Инициализация модулей
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        processor = DataProcessor(collector)
        
        # Получение и фильтрация пар
        all_pairs = collector.get_all_usdt_pairs()
        filtered_pairs = processor.filter_pairs_by_volume_and_price(
            all_pairs,
            min_volume=data['min_volume'],
            min_price=min_price,
            max_price=max_price
        )
        
        pairs_to_analyze = filtered_pairs[:data['max_pairs']]
        
        return jsonify({
            'success': True,
            'pairs_count': len(pairs_to_analyze),
            'pairs': pairs_to_analyze,
            'total_pairs': len(all_pairs),
            'filtered_pairs': len(filtered_pairs)
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
        data = get_request_data(['api_key', 'api_secret', 'pair', 'initial_balance', 'grid_range_pct', 'grid_step_pct'])
        
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
        data = get_request_data(['api_key', 'api_secret', 'pair', 'method'])
        
        # Инициализация
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        grid_analyzer = GridAnalyzer(collector)
        optimizer = GridOptimizer(grid_analyzer, TAKER_COMMISSION_RATE)
        
        # Получение данных
        df = collector.get_historical_data(data['pair'], '1h', 2000)
        
        # Оптимизация
        if data['method'] == 'genetic':
            population_size = data.get('population_size', 20)
            generations = data.get('generations', 10)
            results = optimizer.optimize_genetic(
                df=df,
                initial_balance=1000,
                population_size=population_size,
                generations=generations,
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

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка состояния API для Railway"""
    return jsonify({
        'status': 'healthy',
        'version': 'full',
        'platform': 'Universal (Vercel/Railway)',
        'features': [
            'Grid Trading Simulation',
            'Auto Optimization',
            'Genetic Algorithm',
            'Adaptive Grid Search',
            'Full Analytics'
        ],
        'timestamp': datetime.now().isoformat()
    })

# Для локального тестирования и Railway
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# Для Vercel - правильная сигнатура WSGI handler'а
def handler(event, context):
    """Serverless функция для Vercel"""
    from werkzeug.wrappers import Request, Response
    from io import StringIO
    import sys
    
    # Создаем request из event
    request = Request.from_values(
        path=event.get('path', '/'),
        method=event.get('httpMethod', 'GET'),
        headers=event.get('headers', {}),
        data=event.get('body', ''),
        query_string=event.get('queryStringParameters', {})
    )
    
    # Обрабатываем через Flask app
    with app.test_request_context():
        response = app.full_dispatch_request()
        
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
    }

# Альтернативный handler для совместимости
def app_handler(environ, start_response):
    """WSGI совместимый handler"""
    return app(environ, start_response)
