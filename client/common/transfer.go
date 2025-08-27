package common

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"strconv"
)

const (
	magicBET = "BET0"
	magicACK = "ACK0"
)

// ---------- framing: 4 bytes big-endian length + payload ----------

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
	n := binary.BigEndian.Uint32(hdr)
	if n == 0 {
		return []byte{}, nil
	}
	return readN(conn, int(n))
}

// ---------- helpers de strings (len:uint16 + bytes) ----------

func putU16(buf *bytes.Buffer, v uint16) {
	var tmp [2]byte
	binary.BigEndian.PutUint16(tmp[:], v)
	buf.Write(tmp[:])
}

func getU16(r *bytes.Reader) (uint16, error) {
	var tmp [2]byte
	if _, err := io.ReadFull(r, tmp[:]); err != nil {
		return 0, err
	}
	return binary.BigEndian.Uint16(tmp[:]), nil
}

func putU32(buf *bytes.Buffer, v uint32) {
	var tmp [4]byte
	binary.BigEndian.PutUint32(tmp[:], v)
	buf.Write(tmp[:])
}

func putStr(buf *bytes.Buffer, s string) error {
	if len(s) > 0xFFFF {
		return fmt.Errorf("string too long: %d", len(s))
	}
	putU16(buf, uint16(len(s)))
	buf.WriteString(s)
	return nil
}

func getStr(r *bytes.Reader) (string, error) {
	n, err := getU16(r)
	if err != nil {
		return "", err
	}
	if n == 0 {
		return "", nil
	}
	b := make([]byte, n)
	if _, err := io.ReadFull(r, b); err != nil {
		return "", err
	}
	return string(b), nil
}

// ---------- API de protocolo ----------

// SendBet serializa una apuesta con el protocolo binario y la envía.
func SendBet(conn net.Conn, bet *Bet) error {
	var buf bytes.Buffer

	// magic
	buf.WriteString(magicBET)

	// agency: convertir string -> uint16
	agencyU64, err := strconv.ParseUint(bet.Agency, 10, 16)
	if err != nil {
		return fmt.Errorf("invalid agency %q: %w", bet.Agency, err)
	}
	putU16(&buf, uint16(agencyU64))

	// first/last/document
	if err := putStr(&buf, bet.FirstName); err != nil {
		return err
	}
	if err := putStr(&buf, bet.LastName); err != nil {
		return err
	}
	if err := putStr(&buf, bet.Document); err != nil {
		return err
	}

	// birthdate: 10 bytes YYYY-MM-DD
	if len(bet.Birthdate) != 10 {
		return fmt.Errorf("birthdate must be YYYY-MM-DD, got %q", bet.Birthdate)
	}
	buf.WriteString(bet.Birthdate)

	// number: convertir string -> uint32
	numU64, err := strconv.ParseUint(bet.Number, 10, 32)
	if err != nil {
		return fmt.Errorf("invalid number %q: %w", bet.Number, err)
	}
	putU32(&buf, uint32(numU64))

	// frame
	return writeFrame(conn, buf.Bytes())
}

// ReadAck lee un ACK binario del servidor.
func ReadAck(conn net.Conn) (bool, string, error) {
	frame, err := readFrame(conn)
	if err != nil {
		return false, "", err
	}
	r := bytes.NewReader(frame)

	// magic
	m := make([]byte, 4)
	if _, err := io.ReadFull(r, m); err != nil {
		return false, "", err
	}
	if string(m) != magicACK {
		return false, "", errors.New("invalid ACK magic")
	}

	// ok byte
	okByte, err := r.ReadByte()
	if err != nil {
		return false, "", err
	}
	ok := okByte == 1

	if ok {
		return true, "", nil
	}

	// error string (len+bytes)
	msg, err := getStr(r)
	if err != nil {
		return false, "", err
	}
	if msg == "" {
		msg = "server returned ok=false"
	}
	return false, msg, errors.New(msg)
}
