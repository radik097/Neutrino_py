"""NEUTRINO Python module.

The public API intentionally exposes three classes:

- Server: local/server-side TCP relay endpoint.
- Client: local/client-side connector.
- Doctor: environment and dependency diagnostics.
"""

from .core import Client, Doctor, Server

__all__ = ["Server", "Client", "Doctor"]

