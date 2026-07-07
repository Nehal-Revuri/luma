import json
import requests

from core.configs.config import MODEL, OLLAMA_URL


def might_be_file_action(user_input):
    command = user_input.lower().strip()

    if command.startswith("delete "):
        return False

    action_words = [
        "find",
        "locate",
        "show me",
        "open",
        "reveal",
        "pull up",
        "bring up",
        "where is"
    ]

    file_words = [
        "file",
        "folder",
        "pdf",
        "doc",
        "document",
        "download",
        "screenshot",
        "image",
        "photo",
        "resume",
        "essay",
        "schematic",
        "kicad"
    ]

    return any(word in command for word in action_words) and any(word in command for word in file_words)


def ask_luma_for_tool(user_input):
    tool_prompt = f"""
You are LUMA's tool router.

Your job is to decide whether the user is asking LUMA to perform a file-finding action.

Available tools:
1. find_and_reveal_file
   Use ONLY when the user clearly wants to locate, find, show, reveal, open, or pull up a file/folder on this computer.

Return ONLY valid JSON. No explanation.

Valid tool examples:
- "find my resume"
- "show me the Arduino PDF"
- "open the KiCad schematic"
- "pull up the file about LUMA"
- "locate my college essay"
- "reveal the downloads file about taxes"

Invalid examples. Return "none":
- "what is a file?"
- "how do I find files in Finder?"
- "what files should I create?"
- "explain file systems"
- "where should I store LUMA?"
- "can you help me organize files?"
- "what is my LUMA architecture?"
- "how does memory work?"
- "delete anything"

Rules:
- If the user is asking a conceptual question, return "none".
- If the user is asking for advice, return "none".
- If the user is asking how to do something, return "none".
- If the user mentions files but does not ask to locate/open/reveal a specific file, return "none".
- If the user says "delete", return "none".
- Use the tool only when there is a concrete search target.
- The query should be the shortest useful keyword phrase, not the full sentence.

Schema:
{{
  "tool": "find_and_reveal_file" | "none",
  "args": {{
    "query": "keyword phrase"
  }}
}}

User request:
{user_input}
"""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": tool_prompt}],
        "stream": False,
        "keep_alive": "30m",
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 100
        }
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload)
        r.raise_for_status()
        content = r.json()["message"]["content"].strip()

        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            return {"tool": "none", "args": {}}

        return json.loads(content[start:end])

    except Exception:
        return {"tool": "none", "args": {}}
