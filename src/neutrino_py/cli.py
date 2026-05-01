"""CLI for Server, Client, and Doctor."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from .core import Client, Doctor, Server


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


async def _run_server(args: argparse.Namespace) -> int:
    server = Server(args.host, args.port)
    print(f"Serving on {args.host}:{args.port}")
    await server.serve_forever()
    return 0


async def _run_client(args: argparse.Namespace) -> int:
    client = Client(args.host, args.port, timeout=args.timeout)
    try:
        response = await client.send(args.message.encode("utf-8"))
        print(response.decode("utf-8", errors="replace"))
        return 0
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neutrino-py")
    sub = parser.add_subparsers(dest="command", required=True)

    server = sub.add_parser("server", help="run server endpoint")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", default=8787, type=int)

    client = sub.add_parser("client", help="send one message to server")
    client.add_argument("--host", default="127.0.0.1")
    client.add_argument("--port", default=8787, type=int)
    client.add_argument("--timeout", default=10.0, type=float)
    client.add_argument("message", nargs="?", default="ping")

    doctor = sub.add_parser("doctor", help="run environment diagnostics")
    doctor.add_argument("--timeout", default=3.0, type=float)

    args = parser.parse_args(argv)
    if args.command == "server":
        return asyncio.run(_run_server(args))
    if args.command == "client":
        return asyncio.run(_run_client(args))
    if args.command == "doctor":
        print(_json(Doctor(timeout=args.timeout).run()))
        return 0
    parser.error("unknown command")
    return 2

