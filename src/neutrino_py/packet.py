"""Small binary packet helpers used by Server and Client."""

from __future__ import annotations

import struct
from typing import Tuple

MAGIC = b"NTRN"
VERSION = 1
HEADER = struct.Struct("!4sBII")
MAX_PAYLOAD = 8 * 1024 * 1024


def encode_packet(sequence: int, payload: bytes, flags: int = 0) -> bytes:
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    if flags < 0:
        raise ValueError("flags must be non-negative")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload is too large")
    return HEADER.pack(MAGIC, VERSION, sequence, flags) + payload


def decode_packet(data: bytes) -> Tuple[int, int, bytes]:
    if len(data) < HEADER.size:
        raise ValueError("packet is shorter than header")
    magic, version, sequence, flags = HEADER.unpack(data[: HEADER.size])
    if magic != MAGIC:
        raise ValueError("invalid packet magic")
    if version != VERSION:
        raise ValueError("unsupported packet version")
    return sequence, flags, data[HEADER.size :]


def frame(data: bytes) -> bytes:
    if len(data) > MAX_PAYLOAD:
        raise ValueError("frame is too large")
    return struct.pack("!I", len(data)) + data


def unframe_prefix(buffer: bytearray) -> bytes | None:
    if len(buffer) < 4:
        return None
    size = struct.unpack("!I", buffer[:4])[0]
    if size > MAX_PAYLOAD:
        raise ValueError("incoming frame is too large")
    if len(buffer) < 4 + size:
        return None
    payload = bytes(buffer[4 : 4 + size])
    del buffer[: 4 + size]
    return payload

