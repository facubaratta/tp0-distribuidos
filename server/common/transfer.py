import socket, struct
from common.utils import Bet

MAGIC_BET0 = b"BET0"
MAGIC_BCH0 = b"BCH0"
MAGIC_ACK0 = b"ACK0"
MAGIC_DONE = b"DONE"
MAGIC_QWIN = b"QWIN"
MAGIC_WINS = b"WINS"

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError("socket closed during recv")
        buf.extend(chunk)
    return bytes(buf)

def read_frame(sock: socket.socket) -> bytes:
    (length,) = struct.unpack(">I", _recv_exact(sock, 4))
    return _recv_exact(sock, length) if length else b""

def write_frame(sock: socket.socket, payload: bytes):
    sock.sendall(struct.pack(">I", len(payload)) + payload)

# --------- decode helpers ----------
def _read_u16(buf, pos): return struct.unpack_from(">H", buf, pos)[0], pos+2
def _read_u32(buf, pos): return struct.unpack_from(">I", buf, pos)[0], pos+4
def _read_str(buf, pos):
    ln, pos = _read_u16(buf, pos)
    return bytes(buf[pos:pos+ln]).decode(), pos+ln

def _write_u16(barr, v): barr.extend(struct.pack(">H", v))
def _write_u32(barr, v): barr.extend(struct.pack(">I", v))
def _write_str(barr, s: str):
    data = s.encode()
    _write_u16(barr, len(data))
    barr.extend(data)

def _decode_one_bet(buf: memoryview, pos: int):
    agency, pos = _read_u32(buf, pos)
    first, pos = _read_str(buf, pos)
    last, pos  = _read_str(buf, pos)
    doc, pos   = _read_str(buf, pos)
    birth, pos = _read_str(buf, pos)
    number, pos = _read_u32(buf, pos)
    return Bet(str(agency), first, last, doc, birth, str(number)), pos

# --------- read batch ---------
def read_batch(sock: socket.socket):
    f = read_frame(sock)
    if len(f) < 6 or f[:4] != MAGIC_BCH0:
        raise ValueError("bad BCH0")
    buf = memoryview(f)
    pos = 4
    count, pos = _read_u16(buf, pos)
    bets = []
    for _ in range(count):
        bet, pos = _decode_one_bet(buf, pos)
        bets.append(bet)
    return bets

def send_ack(sock: socket.socket, ok: bool, count: int):
    payload = bytearray()
    payload.extend(MAGIC_ACK0)
    payload.append(1 if ok else 0)
    _write_u16(payload, count)
    write_frame(sock, payload)

def read_done(sock: socket.socket) -> int:
    """Devuelve agency_id (int)."""
    f = read_frame(sock)
    if len(f) < 8 or f[:4] != MAGIC_DONE:
        raise ValueError("bad DONE")
    buf = memoryview(f)
    _, pos = 4, 4
    agency_id, pos = _read_u32(buf, pos)
    return int(agency_id)

def send_done(sock: socket.socket, agency_id: int):
    payload = bytearray()
    payload.extend(MAGIC_DONE)
    _write_u32(payload, int(agency_id))
    write_frame(sock, payload)

def read_query_winners(sock: socket.socket) -> int:
    """Devuelve agency_id (int) pedido en la consulta."""
    f = read_frame(sock)
    if len(f) < 8 or f[:4] != MAGIC_QWIN:
        raise ValueError("bad QWIN")
    buf = memoryview(f)
    _, pos = 4, 4
    agency_id, pos = _read_u32(buf, pos)
    return int(agency_id)

def send_query_winners(sock: socket.socket, agency_id: int):
    payload = bytearray()
    payload.extend(MAGIC_QWIN)
    _write_u32(payload, int(agency_id))
    write_frame(sock, payload)

def send_winners(sock: socket.socket, documents: list[str]):
    payload = bytearray()
    payload.extend(MAGIC_WINS)
    _write_u16(payload, len(documents))
    for dni in documents:
        _write_str(payload, dni)
    write_frame(sock, payload)

def read_winners(sock: socket.socket) -> list[str]:
    f = read_frame(sock)
    if len(f) < 6 or f[:4] != MAGIC_WINS:
        raise ValueError("bad WINS")
    buf = memoryview(f)
    pos = 4
    count, pos = _read_u16(buf, pos)
    out = []
    for _ in range(count):
        s, pos = _read_str(buf, pos)
        out.append(s)
    return out
