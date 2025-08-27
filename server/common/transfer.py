import socket, struct
from common.utils import Bet

MAGIC_BET0 = b"BET0"
MAGIC_BCH0 = b"BCH0"
MAGIC_ACK0 = b"ACK0"

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
    payload.extend(struct.pack(">H", count))
    write_frame(sock, payload)