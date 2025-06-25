"""
Облегчённая Flask API для Vercel с ограничением 250MB
Без pandas, matplotlib - только основная функциональность
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import numpy as np

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Базовые импорты без тяжёлых библиотек
from modules.collector_lite import BinanceDataCollector

app = Flask(__name__)

# Константы комиссий Binance
MAKER_COMMISSION_RATE = 0.0002  # 0.02%
TAKER_COMMISSION_RATE = 0.0005  # 0.05%

# Облегчённый HTML шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Binance Grid Trading - Lite</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { 
            max-width: 1200px; 
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
        .card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .results {
            margin-top: 30px;
        }
        .loading {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 1000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s;
        }
        .loading.show {
            opacity: 1;
            visibility: visible;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top: 4px solid white;
            width: 50px;
            height: 50px;
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
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Binance Grid Trading</h1>
            <p>Lite версия для Vercel (под 250MB лимит)</p>
            <div class="warning">
                ⚠️ Облегчённая версия: основная функциональность доступна, 
                полные возможности Grid Trading и оптимизации требуют локального запуска
            </div>
        </div>

        <div class="card">
            <h3>📊 Анализ торговых пар</h3>
            <p>Получение списка активных торговых пар с Binance</p>
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

        <div class="card">
            <h3>⚙️ API Настройки</h3>
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
                <p><strong>Версия:</strong> Lite (оптимизировано для Vercel 250MB лимит)</p>
                <p><strong>Доступно:</strong></p>
                <ul>
                    <li>✅ Анализ торговых пар</li>
                    <li>✅ Получение данных с Binance</li>
                    <li>✅ Базовые расчёты</li>
                </ul>
                <p><strong>Требует локального запуска:</strong></p>
                <ul>
                    <li>📊 Grid Trading симуляция</li>
                    <li>🤖 Автоматическая оптимизация</li>
                    <li>📈 Продвинутая аналитика</li>
                </ul>
            </div>
        </div>

        <div id="analysisResults" class="results" style="display: none;">
            <div id="analysisContent"></div>
        </div>
    </div>

    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div class="loading-text" id="loadingText">Обработка запроса...</div>
    </div>

    <script>
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

        function loadCredentials() {
            const apiKey = localStorage.getItem('binance_api_key') || '';
            const apiSecret = localStorage.getItem('binance_api_secret') || '';
            
            document.getElementById('apiKey').value = apiKey;
            document.getElementById('apiSecret').value = apiSecret;
        }

        function getCredentials() {
            const apiKey = localStorage.getItem('binance_api_key');
            const apiSecret = localStorage.getItem('binance_api_secret');
            
            if (!apiKey || !apiSecret) {
                showMessage('error', 'Пожалуйста, введите API ключи в настройках');
                return null;
            }
            
            return { apiKey, apiSecret };
        }

        function showMessage(type, message) {
            const existingMessages = document.querySelectorAll('.error, .success, .warning');
            existingMessages.forEach(msg => msg.remove());
            
            const messageDiv = document.createElement('div');
            messageDiv.className = type;
            messageDiv.textContent = message;
            
            document.querySelector('.container').appendChild(messageDiv);
            
            setTimeout(() => messageDiv.remove(), 5000);
        }

        function showLoading(text = 'Обработка запроса...') {
            document.getElementById('loadingText').textContent = text;
            document.getElementById('loading').classList.add('show');
        }

        function hideLoading() {
            document.getElementById('loading').classList.remove('show');
        }

        window.onload = function() {
            loadCredentials();
        };

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
    """API для анализа торговых пар (облегчённая версия)"""
    try:
        data = request.json
        
        # Инициализация модуля сбора данных
        collector = BinanceDataCollector(data['api_key'], data['api_secret'])
        
        # Получение списка всех USDT пар
        all_pairs = collector.get_all_usdt_pairs()
        
        # Простая фильтрация по количеству
        filtered_pairs = all_pairs[:data['max_pairs']]
        
        return jsonify({
            'success': True,
            'pairs_count': len(filtered_pairs),
            'pairs': filtered_pairs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка состояния API"""
    return jsonify({
        'status': 'healthy',
        'version': 'lite',
        'description': 'Binance Grid Trading - Lite version for Vercel 250MB limit'
    })

# Для локального тестирования
if __name__ == '__main__':
    app.run(debug=True)

# Для Vercel
def handler(request):
    return app(request.environ, lambda status, headers: None)
