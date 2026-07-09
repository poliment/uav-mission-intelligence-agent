from __future__ import annotations

import math
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


def embed_text(text: str) -> dict[str, float]:
    features: dict[str, float] = {}
    normalized = text.lower()
    tokens = TOKEN_PATTERN.findall(normalized)
    for token in tokens:
        features[token] = features.get(token, 0.0) + 1.0
        if len(token) >= 3:
            for index in range(len(token) - 2):
                key = f"char:{token[index:index + 3]}"
                features[key] = features.get(key, 0.0) + 0.5
    return _l2_normalize(features)


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return round(sum(value * right.get(key, 0.0) for key, value in left.items()), 6)


def _l2_normalize(features: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in features.values()))
    if norm == 0:
        return {}
    return {key: value / norm for key, value in features.items()}
