import logging, socket
from common.transfer import (
    MAGIC_BCH0, MAGIC_DONE, MAGIC_QWIN,
    _decode_one_bet, _read_u16, _read_u32,
    send_ack, send_winners
)
from common.utils import has_won, load_bets, store_bets

def process_frame(self, frame: bytes, client_sock: socket.socket) -> bool:
    if len(frame) < 4:
        raise ValueError("short frame")
    magic = frame[:4]

    if magic == MAGIC_BCH0:
        buf = memoryview(frame); pos = 4
        count, pos = _read_u16(buf, pos)
        bets = []
        for _ in range(count):
            bet, pos = _decode_one_bet(buf, pos)
            bets.append(bet)
        store_bets(bets)
        logging.info("action: apuesta_recibida | result: success | cantidad: %d", len(bets))
        send_ack(client_sock, ok=True, count=len(bets))
        return True  # cerrar socket

    if magic == MAGIC_DONE:
        buf = memoryview(frame); pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)
        self.done_agencies.add(agency_id)

        # ¿ya están todos?
        if not self.draw_done and len(self.done_agencies) >= self.expected_clients:
            winners = {}
            for b in load_bets():
                if has_won(b):
                    winners.setdefault(b.agency, []).append(b.document)
            self.winners_by_agency = winners
            self.draw_done = True
            logging.info("action: sorteo | result: success")

            # Responder todos los QWIN pendientes y cerrar sus sockets
            pending = self._pending_qwin
            self._pending_qwin = []
            for s, ag in pending:
                try:
                    docs = self.winners_by_agency.get(ag, [])
                    send_winners(s, docs)
                finally:
                    try: s.close()
                    except: pass
        return True  # DONE no tiene respuesta; cerrar

    if magic == MAGIC_QWIN:
        buf = memoryview(frame); pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)

        if not self.draw_done:
            # Encolar y mantener abierto
            self._pending_qwin.append((client_sock, agency_id))
            return False
        # Ya hay sorteo → responder ahora
        docs = self.winners_by_agency.get(agency_id, [])
        send_winners(client_sock, docs)
        return True

    raise ValueError("unknown frame magic")