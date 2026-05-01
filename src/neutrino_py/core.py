"""Public Server, Client, and Doctor classes."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import platform
import socket
import ssl
import sys
import time
from typing import Callable, Dict, Iterable, List, Optional

from . import lowlevel
from .packet import decode_packet, encode_packet, frame, unframe_prefix


class Server:
    """Async TCP server endpoint for NEUTRINO packet frames."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8787,
        handler: Optional[Callable[[bytes], bytes]] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.handler = handler or (lambda payload: payload)
        self._server: asyncio.AbstractServer | None = None
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in list(self._clients):
            writer.close()
            await writer.wait_closed()
        self._clients.clear()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._clients.add(writer)
        buffer = bytearray()
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    raw = unframe_prefix(buffer)
                    if raw is None:
                        break
                    sequence, flags, payload = decode_packet(raw)
                    response = self.handler(payload)
                    writer.write(frame(encode_packet(sequence, response, flags)))
                    await writer.drain()
        finally:
            self._clients.discard(writer)
            writer.close()
            await writer.wait_closed()


class Client:
    """Async TCP client endpoint for sending NEUTRINO packet frames."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8787, timeout: float = 10.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._sequence = 0

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=self.timeout
        )

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def send(self, payload: bytes, flags: int = 0) -> bytes:
        if self._reader is None or self._writer is None:
            await self.connect()
        assert self._reader is not None
        assert self._writer is not None

        sequence = self._sequence
        self._sequence += 1
        self._writer.write(frame(encode_packet(sequence, payload, flags)))
        await self._writer.drain()

        raw = await self._read_frame()
        response_sequence, _response_flags, response = decode_packet(raw)
        if response_sequence != sequence:
            raise RuntimeError(
                f"response sequence mismatch: expected {sequence}, got {response_sequence}"
            )
        return response

    async def ping(self) -> Dict[str, object]:
        started = time.monotonic()
        response = await self.send(b"ping")
        return {
            "ok": response == b"ping",
            "rtt_ms": round((time.monotonic() - started) * 1000, 3),
        }

    async def _read_frame(self) -> bytes:
        assert self._reader is not None
        header = await asyncio.wait_for(self._reader.readexactly(4), timeout=self.timeout)
        size = int.from_bytes(header, "big")
        payload = await asyncio.wait_for(self._reader.readexactly(size), timeout=self.timeout)
        return payload


class Doctor:
    """Check Python, DLL, port, network, and low-level packet prerequisites."""

    DEFAULT_DLLS = ("ws2_32.dll", "iphlpapi.dll", "dnsapi.dll", "crypt32.dll", "bcrypt.dll")
    DEFAULT_MODULES = ("asyncio", "ctypes", "socket", "ssl")

    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    def run(
        self,
        ports: Iterable[int] = (8787,),
        internet_targets: Iterable[tuple[str, int]] = (("1.1.1.1", 443), ("8.8.8.8", 53)),
    ) -> Dict[str, object]:
        return {
            "system": self.system_info(),
            "python_modules": self.python_modules(self.DEFAULT_MODULES),
            "dlls": self.dlls(self.DEFAULT_DLLS),
            "ports": self.ports(ports),
            "internet": self.internet(internet_targets),
            "dns": self.dns("github.com"),
            "tls": self.tls(),
            "low_level": self.low_level(),
        }

    def system_info(self) -> Dict[str, object]:
        return {
            "platform": platform.platform(),
            "windows": os.name == "nt",
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "python_architecture": platform.architecture()[0],
            "python_32bit": lowlevel.python_is_32bit(),
            "openssl": ssl.OPENSSL_VERSION,
        }

    def python_modules(self, names: Iterable[str]) -> Dict[str, bool]:
        return {name: importlib.util.find_spec(name) is not None for name in names}

    def dlls(self, names: Iterable[str]) -> Dict[str, bool]:
        return lowlevel.find_dlls(names)

    def ports(self, ports: Iterable[int], host: str = "127.0.0.1") -> Dict[int, Dict[str, object]]:
        result = {}
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            try:
                sock.bind((host, port))
                result[port] = {"available": True, "host": host}
            except OSError as exc:
                result[port] = {"available": False, "host": host, "error": str(exc)}
            finally:
                sock.close()
        return result

    def internet(self, targets: Iterable[tuple[str, int]]) -> List[Dict[str, object]]:
        return [lowlevel.can_connect(host, port, self.timeout) for host, port in targets]

    def dns(self, host: str) -> Dict[str, object]:
        try:
            addresses = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            return {"ok": True, "host": host, "addresses": sorted({item[4][0] for item in addresses})}
        except OSError as exc:
            return {"ok": False, "host": host, "error": str(exc)}

    def tls(self, host: str = "github.com", port: int = 443) -> Dict[str, object]:
        context = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                    return {
                        "ok": True,
                        "host": host,
                        "port": port,
                        "version": tls_sock.version(),
                        "cipher": tls_sock.cipher()[0],
                    }
        except OSError as exc:
            return {"ok": False, "host": host, "port": port, "error": str(exc)}

    def low_level(self) -> Dict[str, object]:
        return {
            "process_architecture": lowlevel.process_architecture(),
            "winsock_raw_ipv4_icmp": lowlevel.probe_raw_ipv4_socket(),
        }

