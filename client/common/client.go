package common

import (
	"io"
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

func (c *Client) StartClientLoop(sigChan chan os.Signal, src BetSource, batchMax int, maxBytes int) {
	defer src.Close()

	var pending *Bet
	for {
		select {
		case <-sigChan:
			log.Infof("action: shutdown | result: success | client_id: %v", c.config.ID)
			return
		default:
		}

		batch := make([]*Bet, 0, batchMax)
		for len(batch) < batchMax {
			var bet *Bet
			var err error

			if pending != nil {
				bet = pending
				pending = nil
			} else {
				bet, err = src.Next()
				if err != nil {
					if err == io.EOF {
						break
					}
					log.Errorf("action: read_next_bet | result: fail | client_id: %v | error: %v", c.config.ID, err)
					return
				}
			}

			// If adding this bet would exceed maxBytes, defer it to next batch
			if len(batch) == 0 {
				// single bet case must fit
				if 4+2+betWireSize(bet)+4 > maxBytes || BatchFrameSize([]*Bet{bet}) > maxBytes { // defensive
					log.Criticalf("single bet exceeds maxBytes (%d)", maxBytes)
					return
				}
				batch = append(batch, bet)
				continue
			}

			tentative := append(batch, bet)
			if BatchFrameSize(tentative) > maxBytes {
				pending = bet
				break
			}
			batch = tentative
		}

		if len(batch) == 0 {
			break
		}

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

		select {
		case <-sigChan:
			log.Infof("action: shutdown | result: success | client_id: %v", c.config.ID)
			return
		case <-time.After(c.config.LoopPeriod):
		}
	}
	log.Debugf("action: batches_done | result: success | client_id: %v", c.config.ID)
}
