import logging, socket
from common.transfer import (
    MAGIC_BCH0, MAGIC_DONE, MAGIC_QWIN,
    _decode_one_bet, _read_u16, _read_u32,
    send_ack, send_winners
)
from common.utils import has_won, load_bets, store_bets

# Returns si deberia cerrar
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
    
    draw_done_attr = getattr(self, 'draw_done_event')
    is_draw_done = draw_done_attr.is_set()
    set_draw_done = draw_done_attr.set
    wait_draw_done = draw_done_attr.wait

    if magic == MAGIC_DONE:
        buf = memoryview(frame); pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)
        try:
            self.done_agencies[agency_id] = True
        except Exception:
            pass

        # ¿ya están todos?
        if (not is_draw_done) and len(self.done_agencies) >= self.expected_clients:
            winners = {}
            for b in load_bets():
                if has_won(b):
                    winners.setdefault(b.agency, []).append(b.document)
            try:
                try:
                    for k in list(self.winners_by_agency.keys()):
                        del self.winners_by_agency[k]
                except Exception:
                    pass
                for ag, docs in winners.items():
                    self.winners_by_agency[int(ag)] = list(docs)
            finally:
                set_draw_done()
            logging.info("action: sorteo | result: success")
        return True  # DONE no tiene respuesta; cerrar

    if magic == MAGIC_QWIN:
        buf = memoryview(frame); pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)

        if not is_draw_done:
            wait_draw_done()
        try:
            docs = self.winners_by_agency.get(agency_id, [])
        except Exception:
            docs = []
        send_winners(client_sock, docs)
        return True

    raise ValueError("unknown frame magic")
