import re

def normalize_command(text: str) -> str:

    text = text.lower()

    # Remove punctuation

    text = re.sub(r"[^\w\s]", "", text)

    # Collapse whitespace

    text = " ".join(text.split())

    return text
