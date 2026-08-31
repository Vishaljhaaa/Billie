from __future__ import annotations

import re
from functools import lru_cache

from nltk.stem import WordNetLemmatizer


@lru_cache(maxsize=1)
def _wordnet_lemmatizer() -> WordNetLemmatizer:
    return WordNetLemmatizer()


def lemmatize_token(token: str) -> str:
    try:
        return _wordnet_lemmatizer().lemmatize(token)
    except LookupError:
        return token


def tokenize_and_lemmatize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [lemmatize_token(token) for token in tokens]
