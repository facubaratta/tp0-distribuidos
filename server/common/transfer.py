import struct
import json
import socket
from typing import Dict
from common.utils import Bet 

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
    return _recv_exact(sock, length)

def write_frame(sock: socket.socket, payload: bytes):
    header = struct.pack(">I", len(payload))
    sock.sendall(header)
    sock.sendall(payload)


def read_json(sock: socket.socket) -> Dict:
    data = read_frame(sock)
    return json.loads(data.decode("utf-8"))

def write_json(sock: socket.socket, obj: Dict):
    payload = json.dumps(obj).encode("utf-8")
    write_frame(sock, payload)


class ProtocolError(Exception):
    pass

def read_bet(sock: socket.socket) -> Bet:
    """
    Lee un JSON enmarcado y lo convierte a utils.Bet.
    Claves esperadas: agency, first_name, last_name, document, birthdate, number
    """
    obj = read_json(sock)
    try:
        return Bet(
            obj["agency"],
            obj["first_name"],
            obj["last_name"],
            obj["document"],
            obj["birthdate"],
            obj["number"],
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ProtocolError(str(e))

from typing import Optional, Dict, Union

def send_ack(sock: socket.socket, ok: bool = True, error: Optional[str] = None):
    msg: Dict[str, Union[bool, str]] = {"ok": bool(ok)}
    if not ok and error:
        msg["error_message"] = str(error)
    write_json(sock, msg)