import os
import socket
import logging

from common.transfer import read_frame, send_ack
from common.process import process_frame

class Server:
    def __init__(self, port, listen_backlog):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.running = True
        self.client_sockets = []

        self.expected_clients = int(os.getenv("CLIENTS", "5"))
        self.done_agencies: set[int] = set()
        self.draw_done = False
        self.winners_by_agency: dict[int, list[str]] = {}
        self._pending_qwin = [] 

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
        logging.info('action: shutdown | result: success')

    def run(self):
        while self.running:
            try:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    self.client_sockets.append(client_sock)
                    # Blocking, one-at-a-time
                    self.__handle_client_connection(client_sock)
            except OSError as e:
                if not self.running:
                    break
                logging.error(f'action: accept_error | error: {e}')

    def __handle_client_connection(self, client_sock: socket.socket):
        should_close = True
        try:
            frame = read_frame(client_sock)
            should_close = process_frame(self, frame, client_sock)
        except Exception as e:
            logging.error('action: handle_connection | result: fail | error: %s', e)
            try: send_ack(client_sock, ok=False, count=0)
            except Exception: pass
        finally:
            if should_close:
                try: client_sock.close()
                finally:
                    try: self.client_sockets.remove(client_sock)
                    except ValueError: pass

    def __accept_new_connection(self):
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info('action: accept_connections | result: success | ip: %s', addr[0])
        return c