package common

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"net"
)

// ----- framing: 4 bytes BE length + payload -----

func writeFrame(conn net.Conn, payload []byte) error {
	var hdr [4]byte
	binary.BigEndian.PutUint32(hdr[:], uint32(len(payload)))
	if _, err := conn.Write(hdr[:]); err != nil {
		return err
	}
	_, err := conn.Write(payload)
	return err
}

func readN(conn net.Conn, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(conn, buf) // short-read safe
	return buf, err
}

func readFrame(conn net.Conn) ([]byte, error) {
	hdr, err := readN(conn, 4)
	if err != nil {
		return nil, err
	}
	length := binary.BigEndian.Uint32(hdr)
	if length == 0 {
		return []byte{}, nil
	}
	return readN(conn, int(length))
}

// ----- JSON helpers -----

func writeJSON(conn net.Conn, v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return writeFrame(conn, b)
}

func readJSON(conn net.Conn, v any) error {
	b, err := readFrame(conn)
	if err != nil {
		return err
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	return dec.Decode(v)
}

// ----- Wire types -----

type ackWire struct {
	Ok    bool   `json:"ok"`
	Error string `json:"error,omitempty"`
}

// Bet ya lo tenés en domain.go con tags json:
//   Agency, FirstName, LastName, Document, Birthdate, Number
//   y los tags `json:"agency"` etc.

// ----- API pública -----

func SendBet(conn net.Conn, bet *Bet) error {
	return writeJSON(conn, bet) // las claves ya matchean el server
}

func ReadAck(conn net.Conn) (bool, string, error) {
	var ack ackWire
	if err := readJSON(conn, &ack); err != nil {
		return false, "", err
	}
	if !ack.Ok {
		if ack.Error != "" {
			return false, ack.Error, fmt.Errorf("server error: %s", ack.Error)
		}
		return false, "", fmt.Errorf("server returned ok=false")
	}
	return true, "", nil
}
