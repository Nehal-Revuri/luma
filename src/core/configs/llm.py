import base64
import json
import requests

from core.configs.config import MODEL, OLLAMA_URL, SYSTEM_PROMPT, VISION_MODEL
from core.configs.memory import load_memory, load_knowledge, history, remember_exchange


def build_messages(user_input):
    memory = load_memory()
    knowledge = load_knowledge()

    memory_text = "\n".join(
        f"- User: {m.get('user', '')}\n  LUMA: {m.get('assistant', '')}"
        for m in memory[-6:]
    )

    knowledge_text = "\n".join(
        f"- {k.get('title', 'Untitled')}: {k.get('content', '')}"
        for k in knowledge[-10:]
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if knowledge_text:
        messages.append({
            "role": "system",
            "content": f"Updated knowledge base:\n{knowledge_text}"
        })

    if memory_text:
        messages.append({
            "role": "system",
            "content": f"Relevant prior memory:\n{memory_text}"
        })

    messages.extend(list(history))
    messages.append({"role": "user", "content": user_input})

    return messages


def ask_luma(user_input, on_chunk=None):
    payload = {
        "model": MODEL,
        "messages": build_messages(user_input),
        "stream": True,
        "keep_alive": "30m",
        "think": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 500,
            "num_ctx": 2048
        }
    }

    response_text = ""

    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True) as r:
            r.raise_for_status()

            for line in r.iter_lines():
                if not line:
                    continue

                data = json.loads(line.decode("utf-8"))

                if "message" in data and "content" in data["message"]:
                    chunk = data["message"]["content"]

                    print(chunk, end="", flush=True)
                    response_text += chunk

                    if on_chunk:
                        on_chunk(chunk)

                if data.get("done"):
                    break

        print()

    except Exception as e:
        print(f"\nLUMA error: {e}")
        return ""

    remember_exchange(user_input, response_text)
    return response_text


def ask_luma_vision(image_path, prompt, on_chunk=None, detected_labels=None):
    try:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
    except OSError as error:
        return f"I could not read the inspection image, sir. ({error})"

    if detected_labels:
        prompt = (
            f"{prompt}\n\n"
            f"Local object detector also saw: {', '.join(detected_labels)}."
        )

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt, "images": [encoded]},
        ],
        "stream": True,
        "keep_alive": "30m",
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 400,
        },
    }

    response_text = ""

    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                data = json.loads(line.decode("utf-8"))

                if "message" in data and "content" in data["message"]:
                    chunk = data["message"]["content"]
                    print(chunk, end="", flush=True)
                    response_text += chunk

                    if on_chunk:
                        on_chunk(chunk)

                if data.get("done"):
                    break

        print()
        remember_exchange(prompt, response_text)
        return response_text

    except Exception:
        fallback_prompt = (
            f"{prompt}\n\n"
            f"I could not use the vision model ({VISION_MODEL}). "
            f"Give your best practical insights from any detector hints provided."
        )
        return ask_luma(fallback_prompt, on_chunk=on_chunk)


def warmup():
    try:
        requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "ready"}],
                "stream": False,
                "keep_alive": "30m",
                "think": False,
                "options": {"num_predict": 1}
            },
            timeout=60
        )
    except Exception as e:
        print(f"LUMA warmup failed: {e}")
