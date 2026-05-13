from __future__ import annotations

import hashlib


def make_watermark(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:18]


def attach_watermark(data: dict) -> dict:
    payload = dict(data)
    base = f"{payload.get('user_name','')}|{payload.get('status','')}|{payload.get('timestamp','')}"
    payload["watermark"] = make_watermark(base)
    return payload


def verify_watermark(data: dict) -> bool:
    expected = make_watermark(f"{data.get('user_name','')}|{data.get('status','')}|{data.get('timestamp','')}")
    return data.get("watermark") == expected

