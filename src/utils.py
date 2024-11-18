import json
from typing import Any

def read_json(filename: str) -> dict | list:
    with open(filename, 'r') as f:
        return json.load(f)

def write_json(filename: str, data: Any) -> None:
    with open(filename, 'w') as f:
        json.dump(data, f)