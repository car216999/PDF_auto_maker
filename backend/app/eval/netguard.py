"""네트워크 가드 — 실행 중 외부(비-루프백) 소켓 연결을 감지.

기획서 KPI '외부 호출 0건'을 말이 아닌 실측으로 증명한다.
socket.connect 를 가로채 루프백(127.0.0.1/::1) 외 목적지를 기록한다.
로컬 Ollama·Qdrant 는 루프백이므로 통과, 외부 API 호출은 즉시 잡힌다.
"""
import ipaddress
import socket
from contextlib import contextmanager

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", ""}


def is_local(host: str) -> bool:
    if host in _LOCAL_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost" or host.endswith(".localhost")


class NetGuard:
    def __init__(self) -> None:
        self.external: list[str] = []

    @contextmanager
    def watch(self):
        original = socket.socket.connect
        guard = self

        def patched(self, address):
            try:
                host = address[0] if isinstance(address, (tuple, list)) else str(address)
                if not is_local(host):
                    guard.external.append(host)
            except Exception:
                pass
            return original(self, address)

        socket.socket.connect = patched
        try:
            yield self
        finally:
            socket.socket.connect = original
