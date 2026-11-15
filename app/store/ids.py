"""Identificadores con prefijo + ULID: únicos y ordenables por fecha de creación."""

import os
import threading
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32
_RANDOM_BITS = 80
_lock = threading.Lock()
_last_ms = -1
_last_random = 0


def new_ulid() -> str:
    """ULID monótono: dos identificadores del mismo milisegundo conservan el orden."""
    global _last_ms, _last_random
    with _lock:
        now_ms = time.time_ns() // 1_000_000
        if now_ms <= _last_ms:
            now_ms = _last_ms
            _last_random += 1
            if _last_random >> _RANDOM_BITS:  # Desbordamiento: se pasa al milisegundo siguiente.
                now_ms += 1
                _last_random = int.from_bytes(os.urandom(10))
        else:
            _last_random = int.from_bytes(os.urandom(10))
        _last_ms = now_ms
        value = (now_ms << _RANDOM_BITS) | _last_random
    return "".join(_ALPHABET[(value >> shift) & 31] for shift in range(125, -1, -5))


def new_field_id() -> str:
    return f"fld_{new_ulid()}"
