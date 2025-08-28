import logging
import socket
from server.common.transfer import MAGIC_BCH0, MAGIC_DONE, MAGIC_QWIN, _decode_one_bet, _read_u16, _read_u32, send_ack, send_winners
from server.common.utils import has_won, load_bets, store_bets

def process_frame(self, frame: bytes, client_sock: socket.socket):
    magic = frame[:4]

    if magic == MAGIC_BCH0:
        buf = memoryview(frame)
        pos = 4
        count, pos = _read_u16(buf, pos)
        bets = []
        for _ in range(count):
            bet, pos = _decode_one_bet(buf, pos)
            bets.append(bet)

        store_bets(bets)
        logging.info("action: apuesta_recibida | result: success | cantidad: %d", len(bets))
        send_ack(client_sock, ok=True, count=len(bets))
        return

    if magic == MAGIC_DONE:
        buf = memoryview(frame)
        pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)

        self.done_agencies.add(agency_id)

        if not self.draw_done and len(self.done_agencies) >= self.expected_clients:
            winners: dict[int, list[str]] = {}
            for b in load_bets():
                if has_won(b):
                    winners.setdefault(b.agency, []).append(b.document)
            self.winners_by_agency = winners
            self.draw_done = True
            logging.info("action: sorteo | result: success")
        return

    if magic == MAGIC_QWIN:
        buf = memoryview(frame)
        pos = 4
        agency_id, pos = _read_u32(buf, pos)
        agency_id = int(agency_id)

        docs = self.winners_by_agency.get(agency_id, [])
        send_winners(client_sock, docs)
        return

    raise ValueError("unknown frame magic")