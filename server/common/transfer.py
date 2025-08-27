import struct
import json
import socket
from typing import Dict, List
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

def _to_bet(obj: Dict) -> Bet:
    return Bet(
        obj["agency"],
        obj["first_name"],
        obj["last_name"],
        obj["document"],
        obj["birthdate"],
        obj["number"],
    )
    
def read_batch(sock: socket.socket) -> List[Bet]:
    """
    Lee un JSON enmarcado que debe ser una lista de apuestas
    con las claves: agency, first_name, last_name, document, birthdate, number
    """
    obj = read_json(sock)
    if not isinstance(obj, list):
        raise ProtocolError("expected a JSON array of bets")
    bets: List[Bet] = []
    try:
        for item in obj:
            bets.append(_to_bet(item))
        return bets
    except (KeyError, TypeError, ValueError) as e:
        raise ProtocolError(str(e))

from typing import Optional, Dict, Union

def send_ack(sock: socket.socket, ok: bool = True, error: Optional[str] = None):
    msg: Dict[str, Union[bool, str]] = {"ok": bool(ok)}
    if not ok and error:
        msg["error"] = str(error)
    write_json(sock, msg)