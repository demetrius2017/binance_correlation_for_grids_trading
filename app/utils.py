# Утилиты для работы с API ключами
import json
import os
from typing import Tuple

def save_api_keys(api_key: str, api_secret: str) -> None:
    config = {"api_key": api_key, "api_secret": api_secret}
    with open("config.json", "w") as f:
        json.dump(config, f)

def load_api_keys() -> Tuple[str, str]:
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
            return config.get("api_key", ""), config.get("api_secret", "")
        return "", ""
    except Exception as e:
        print(f"Ошибка при загрузке API ключей: {e}")
        return "", ""
