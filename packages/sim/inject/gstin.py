"""GSTIN checksum — interesting BEC cases pass the check."""

from __future__ import annotations

GSTN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_check_digit(body14: str) -> str:
    factor = 2
    total = 0
    for ch in reversed(body14.upper()):
        code_point = GSTN_CHARS.index(ch)
        addend = factor * code_point
        factor = 1 if factor == 2 else 2
        total += addend // 36 + addend % 36
    remainder = total % 36
    check = (36 - remainder) % 36
    return GSTN_CHARS[check]


def gstin_checksum_ok(gstin: str) -> bool:
    gstin = gstin.strip().upper()
    if len(gstin) != 15:
        return False
    return gstin_check_digit(gstin[:14]) == gstin[14]


def make_valid_gstin(serial: int) -> str:
    pan = f"AAAAA{serial:04d}A"
    body = f"22{pan[:10]}1Z"
    return body + gstin_check_digit(body)
