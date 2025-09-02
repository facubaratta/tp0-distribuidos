import os
import socket
import logging
import multiprocessing as mp
from types import SimpleNamespace

from common.transfer import read_frame, send_ack
from common.process import process_frame

def _worker_handle_connection(expected_clients: int, done_agencies, draw_done_event, winners_by_agency, client_fd: int):
    client_sock = socket.socket(fileno=client_fd)
    state = SimpleNamespace(
        expected_clients=expected_clients,
        done_agencies=done_agencies,
        draw_done_event=draw_done_event,
        winners_by_agency=winners_by_agency,
    )
    should_close = True
    try:
        frame = read_frame(client_sock)
        should_close = process_frame(state, frame, client_sock)
    except Exception as e:
        logging.error('action: handle_connection | result: fail | error: %s', e)
        try:
            send_ack(client_sock, ok=False, count=0)
        except Exception:
            pass
    finally:
        if should_close:
            try:
                client_sock.close()
            except Exception:
                pass

class Server:
    def __init__(self, port, listen_backlog):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.running = True
        self.client_sockets = []

        self.expected_clients = int(os.getenv("CLIENTS", "5"))
        
        self._manager = mp.Manager()
        self.done_agencies = self._manager.dict()
        self.winners_by_agency = self._manager.dict()
        self.draw_done_event = mp.Event()
        self._children: list[mp.Process] = []

    def graceful_shutdown(self):
        self.running = False
        if self._server_socket:
            try:
                self._server_socket.close()
                logging.info('action: close_fd | target: server_socket | result: success')
            except OSError as e:
                logging.error(f'action: close_fd | target: server_socket | result: fail | error: {e}')
        for cs in list(self.client_sockets):
            try:
                cs.close()
                logging.info('action: close_fd | target: client_socket | result: success')
            except OSError as e:
                logging.error(f'action: close_fd | target: client_socket | result: fail | error: {e}')
        # Terminate any lingering worker processes
        for p in list(self._children):
            try:
                if p.is_alive():
                    p.terminate()
                p.join(timeout=1)
            except Exception:
                pass
        logging.info('action: shutdown | result: success')

    def run(self):
        while self.running:
            try:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    self.client_sockets.append(client_sock)
                    p = mp.Process(
                        target=_worker_handle_connection,
                        args=(
                            self.expected_clients,
                            self.done_agencies,
                            self.draw_done_event,
                            self.winners_by_agency,
                            client_sock.fileno(),
                        ),
                        daemon=True,
                    )
                    p.start()
                    self._children.append(p)
                    # Close parent's copy; child owns the fd now
                    try:
                        client_sock.close()
                    finally:
                        try:
                            self.client_sockets.remove(client_sock)
                        except ValueError:
                            pass
                    # Reap finished children occasionally
                    self._children = [ch for ch in self._children if ch.is_alive()]
            except OSError as e:
                if not self.running:
                    break
                logging.error(f'action: accept_error | error: {e}')

    def __accept_new_connection(self):
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info('action: accept_connections | result: success | ip: %s', addr[0])
        return c
