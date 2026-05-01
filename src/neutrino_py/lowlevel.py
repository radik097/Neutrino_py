"""Low-level Windows networking helpers.

This module uses ctypes instead of third-party extensions so it can run on
Windows 7/10/11 x86 when Python itself is 32-bit. The helpers are deliberately
small: they verify DLL availability, initialize Winsock, and probe whether the
process can create raw sockets. Raw packet access requires Administrator rights
on Windows and is limited by the OS networking stack.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import platform
import socket
from typing import Dict, Iterable

AF_INET = 2
SOCK_RAW = 3
IPPROTO_ICMP = 1
INVALID_SOCKET = ctypes.c_size_t(-1).value
SOCKET_ERROR = -1


def is_windows() -> bool:
    return os.name == "nt"


def process_architecture() -> str:
    return platform.architecture()[0]


def python_is_32bit() -> bool:
    return ctypes.sizeof(ctypes.c_void_p) == 4


def find_dlls(names: Iterable[str]) -> Dict[str, bool]:
    result = {}
    for name in names:
        found = ctypes.util.find_library(name)
        if found:
            result[name] = True
            continue
        try:
            ctypes.WinDLL(name) if is_windows() else ctypes.CDLL(name)
            result[name] = True
        except Exception:
            result[name] = False
    return result


def winsock_startup() -> bool:
    if not is_windows():
        return False
    ws2_32 = ctypes.WinDLL("ws2_32.dll")
    data = ctypes.create_string_buffer(512)
    rc = ws2_32.WSAStartup(0x0202, ctypes.byref(data))
    return rc == 0


def winsock_cleanup() -> None:
    if is_windows():
        ctypes.WinDLL("ws2_32.dll").WSACleanup()


def probe_raw_ipv4_socket(protocol: int = IPPROTO_ICMP) -> Dict[str, object]:
    """Probe raw IPv4 socket support through Winsock.

    Returns a diagnostic dictionary instead of raising. This only opens and
    closes a socket; it does not transmit packets.
    """

    if not is_windows():
        return {
            "ok": False,
            "supported": False,
            "error": "raw Winsock probe is only available on Windows",
        }

    ws2_32 = ctypes.WinDLL("ws2_32.dll")
    data = ctypes.create_string_buffer(512)
    startup = ws2_32.WSAStartup(0x0202, ctypes.byref(data))
    if startup != 0:
        return {"ok": False, "supported": False, "error": f"WSAStartup failed: {startup}"}

    ws2_32.socket.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    ws2_32.socket.restype = ctypes.c_size_t
    ws2_32.closesocket.argtypes = [ctypes.c_size_t]
    ws2_32.WSAGetLastError.restype = ctypes.c_int

    handle = ws2_32.socket(AF_INET, SOCK_RAW, protocol)
    if handle == INVALID_SOCKET:
        error_code = ws2_32.WSAGetLastError()
        ws2_32.WSACleanup()
        return {
            "ok": False,
            "supported": True,
            "error": f"socket(AF_INET, SOCK_RAW, {protocol}) failed: WSA {error_code}",
            "hint": "Run as Administrator and check local security policy/firewall.",
        }

    close_rc = ws2_32.closesocket(handle)
    ws2_32.WSACleanup()
    return {
        "ok": close_rc != SOCKET_ERROR,
        "supported": True,
        "handle_opened": True,
        "protocol": protocol,
    }


def can_connect(host: str, port: int, timeout: float) -> Dict[str, object]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}

