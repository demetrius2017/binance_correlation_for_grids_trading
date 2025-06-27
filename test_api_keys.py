"""
Тест загрузки API ключей из различных источников
"""

import os
import json
import requests
from typing import Tuple

def test_api_keys_loading():
    """Тестирует загрузку API ключей"""
    
    def load_api_keys_test() -> Tuple[str, str]:
        """Упрощенная версия функции загрузки для тестирования"""
        try:
            # 1. Переменные окружения
            env_api_key = os.getenv("BINANCE_API_KEY")
            env_api_secret = os.getenv("BINANCE_API_SECRET")
            if env_api_key and env_api_secret:
                print("✅ API ключи найдены в переменных окружения")
                return env_api_key, env_api_secret
            
            # 2. GitHub репозиторий
            try:
                github_url = "https://raw.githubusercontent.com/demetrius2017/binance_correlation_for_grids_trading/main/config.json"
                print(f"🔍 Попытка загрузки из GitHub: {github_url}")
                response = requests.get(github_url, timeout=10)
                print(f"📡 GitHub ответ: {response.status_code}")
                
                if response.status_code == 200:
                    github_config = response.json()
                    github_api_key = github_config.get("api_key", "")
                    github_api_secret = github_config.get("api_secret", "")
                    if github_api_key and github_api_secret:
                        print("✅ API ключи загружены из GitHub репозитория")
                        print(f"🔑 API Key: {github_api_key[:10]}...")
                        print(f"🔐 API Secret: {github_api_secret[:10]}...")
                        return github_api_key, github_api_secret
                    else:
                        print("❌ Ключи в GitHub config.json пустые")
                else:
                    print(f"❌ Не удалось получить config.json из GitHub (код: {response.status_code})")
                        
            except Exception as github_error:
                print(f"⚠️ Ошибка загрузки из GitHub: {github_error}")
            
            # 3. Локальный файл
            if os.path.exists("config.json"):
                print("🔍 Найден локальный config.json")
                with open("config.json", "r") as f:
                    config = json.load(f)
                local_api_key = config.get("api_key", "")
                local_api_secret = config.get("api_secret", "")
                if local_api_key and local_api_secret:
                    print("✅ API ключи загружены из локального config.json")
                    print(f"🔑 API Key: {local_api_key[:10]}...")
                    print(f"🔐 API Secret: {local_api_secret[:10]}...")
                    return local_api_key, local_api_secret
                else:
                    print("❌ Локальный config.json пустой")
            else:
                print("❌ Локальный config.json не найден")
            
            print("❌ API ключи не найдены ни в одном источнике")
            return "", ""
            
        except Exception as e:
            print(f"❌ Общая ошибка при загрузке API ключей: {e}")
            return "", ""

    print("🧪 Тестирование загрузки API ключей")
    print("=" * 50)
    
    api_key, api_secret = load_api_keys_test()
    
    print("\n📊 Результат:")
    if api_key and api_secret:
        print("✅ API ключи успешно загружены!")
        print(f"🔑 Длина API Key: {len(api_key)} символов")
        print(f"🔐 Длина API Secret: {len(api_secret)} символов")
    else:
        print("❌ API ключи не загружены")
    
    print("=" * 50)

if __name__ == "__main__":
    test_api_keys_loading()
