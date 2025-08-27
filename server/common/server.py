import socket
import logging

from common.transfer import read_batch, read_bet, send_ack, ProtocolError
from common.utils import store_bets

class Server:
    def __init__(self, port, listen_backlog):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.running = True
        self.client_sockets = []

    def graceful_shutdown(self, signum=None, frame=None):
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
                    self.__handle_client_connection(client_sock)
            except OSError as e:
                if not self.running:
                    break
                logging.error(f'action: accept_error | error: {e}')

    def __handle_client_connection(self, client_sock):
        try:
            bets = read_batch(client_sock)
            store_bets(bets)
            logging.info("action: apuesta_recibida | result: success | cantidad: %d", len(bets))
            send_ack(client_sock, ok=True)
        except (ProtocolError, OSError, ValueError) as e:
            logging.error('action: handle_client | result: fail | error: %s', e)
            try:
                send_ack(client_sock, ok=False, error=str(e))
            except Exception:
                pass
        finally:
            try:
                client_sock.close()
            finally:
                try:
                    self.client_sockets.remove(client_sock)
                except ValueError:
                    pass

    def __accept_new_connection(self):
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info('action: accept_connections | result: success | ip: %s', addr[0])
        return c