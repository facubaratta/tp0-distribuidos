package common

import (
	"net"
	"os"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
}

type Client struct {
	config ClientConfig
	conn   net.Conn
}

func NewClient(config ClientConfig) *Client {
	return &Client{config: config}
}

func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return err
	}
	c.conn = conn
	return nil
}

func (c *Client) StartClientLoop(sigChan chan os.Signal, allBets []*Bet, batchMax int, maxBytes int) {
	for i := 0; i < len(allBets); {
		select {
		case <-sigChan:
			log.Infof("action: shutdown | result: success | client_id: %v", c.config.ID)
			return
		default:
		}

		// ventana [i, j)
		j := i + batchMax
		if j > len(allBets) {
			j = len(allBets)
		}

		batch := allBets[i:j]

		log.Debugf("action: batch_build | result: looking into if should recalculate | count:%d | bytes:%d | max:%d", len(batch), BatchFrameSize(batch), maxBytes)

		for len(batch) > 1 && BatchFrameSize(batch) > maxBytes {
			batch = batch[:len(batch)-1]
		}

		if len(batch) == 1 && BatchFrameSize(batch) > maxBytes {
			log.Criticalf("single bet exceeds maxBytes (%d)", maxBytes)
			return
		}

		log.Debugf("action: batch_build | result: success | count:%d | bytes:%d | max:%d", len(batch), BatchFrameSize(batch), maxBytes)

		if err := c.createClientSocket(); err != nil {
			return
		}
		if err := SendBatch(c.conn, batch); err != nil {
			_ = c.conn.Close()
			log.Errorf("action: send_batch | result: fail | client_id: %v | error: %v", c.config.ID, err)
			return
		}

		ok, count, err := ReadAck(c.conn)
		_ = c.conn.Close()
		if err != nil || !ok || int(count) != len(batch) {
			log.Errorf("action: receive_ack | result: fail | client_id: %v | error: %v | expected: %d got: %d",
				c.config.ID, err, len(batch), count)
			return
		}

		i += len(batch)

		select {
		case <-sigChan:
			log.Infof("action: shutdown | result: success | client_id: %v", c.config.ID)
			return
		case <-time.After(c.config.LoopPeriod):
		}
	}
	log.Infof("action: batches_done | result: success | client_id: %v", c.config.ID)
}
