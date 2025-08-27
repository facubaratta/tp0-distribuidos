import struct
import socket
from typing import Optional

# utils.Bet(agency, first_name, last_name, document, birthdate, number)
from common.utils import Bet

MAGIC_BET = b"BET0"
MAGIC_ACK = b"ACK0"

# ---------- framing ----------

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError("socket closed during recv")
        buf.extend(chunk)
    return bytes(buf)

def read_frame(sock: socket.socket) -> bytes:
    header = _recv_exact(sock, 4)
    (length,) = struct.unpack(">I", header)
    return _recv_exact(sock, length) if length else b""

def write_frame(sock: socket.socket, payload: bytes):
    header = struct.pack(">I", len(payload))
    sock.sendall(header)
    sock.sendall(payload)

# ---------- helpers (len:uint16 + bytes) ----------

def _read_u16(buf: memoryview, offset: int) -> tuple[int, int]:
    (v,) = struct.unpack_from(">H", buf, offset)
    return v, offset + 2

def _read_u32(buf: memoryview, offset: int) -> tuple[int, int]:
    (v,) = struct.unpack_from(">I", buf, offset)
    return v, offset + 4

def _read_str(buf: memoryview, offset: int) -> tuple[str, int]:
    n, offset = _read_u16(buf, offset)
    s = bytes(buf[offset:offset+n]).decode("utf-8") if n > 0 else ""
    return s, offset + n

def _write_u16(parts: list[bytes], v: int):
    parts.append(struct.pack(">H", v))

def _write_str(parts: list[bytes], s: str):
    b = s.encode("utf-8")
    if len(b) > 0xFFFF:
        raise ValueError("string too long")
    _write_u16(parts, len(b))
    parts.append(b)

# ---------- protocolo ----------

class ProtocolError(Exception):
    pass

def read_bet(sock: socket.socket) -> Bet:
    """
    Lee un frame, verifica magic BET0 y parsea:
      agency:uint16, first_name:str16, last_name:str16, document:str16,
      birthdate:10-bytes ASCII, number:uint32
    Retorna utils.Bet con agency y number en formato string, como requiere utils.Bet.
    """
    frame = read_frame(sock)
    if len(frame) < 4:
        raise ProtocolError("frame too short")

    buf = memoryview(frame)
    if bytes(buf[:4]) != MAGIC_BET:
        raise ProtocolError("invalid BET magic")
    offset = 4

    agency_u16, offset = _read_u16(buf, offset)
    first_name, offset = _read_str(buf, offset)
    last_name,  offset = _read_str(buf, offset)
    document,   offset = _read_str(buf, offset)

    if offset + 10 > len(buf):
        raise ProtocolError("missing birthdate")
    birthdate = bytes(buf[offset:offset+10]).decode("ascii")
    offset += 10

    number_u32, offset = _read_u32(buf, offset)

    # utils.Bet espera strings (convierte internamente a tipos)
    return Bet(
        str(agency_u16),
        first_name,
        last_name,
        document,
        birthdate,
        str(number_u32),
    )

def send_ack(sock: socket.socket, ok: bool = True, error: Optional[str] = None):
    parts: list[bytes] = []
    parts.append(MAGIC_ACK)
    parts.append(b"\x01" if ok else b"\x00")
    if not ok:
        _write_str(parts, error or "error")
    write_frame(sock, b"".join(parts))