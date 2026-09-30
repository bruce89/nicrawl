"""Las pruebas no pueden conectar a Internet; asyncio usa loopback en Windows."""

import socket

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Los tests usan fixtures y transporte falso, nunca red real")

    def local_only(self: socket.socket, address: object) -> None:
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            original_connect(self, address)
            return
        blocked()

    def local_only_ex(self: socket.socket, address: object) -> int:
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect_ex(self, address)
        blocked()
        return -1

    def local_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_create_connection(address, *args, **kwargs)
        blocked()
        raise AssertionError

    monkeypatch.setattr(socket, "create_connection", local_create_connection)
    monkeypatch.setattr(socket.socket, "connect", local_only)
    monkeypatch.setattr(socket.socket, "connect_ex", local_only_ex)
