import json
import os
from collections import deque
from core.configs.config import MEMORY_FILE, KNOWLEDGE_FILE

history = deque(maxlen=8)


def load_json_file(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_memory():
    return load_json_file(MEMORY_FILE, [])


def save_memory(memory):
    save_json_file(MEMORY_FILE, memory[-50:])


def load_knowledge():
    return load_json_file(KNOWLEDGE_FILE, [])


def remember_exchange(user_input, response_text):
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response_text})

    memory = load_memory()
    memory.append({"user": user_input, "assistant": response_text})
    save_memory(memory)
