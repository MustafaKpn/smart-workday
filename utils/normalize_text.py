#app/utils/normalize_text.py

import re

def normalize_text(text: str) -> str:
    """
    Normalize text to reduce LLM variability.gemini
    """
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text