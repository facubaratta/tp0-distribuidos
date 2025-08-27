package common

import (
	"bytes"
	"encoding/binary"
	"errors"
	"io"
	"net"
	"strconv"
)

const (
	magicBET0 = "BET0"
	magicBCH0 = "BCH0"
	magicACK0 = "ACK0"
)

func atoiSafe(s string) int {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

func writeFrame(conn net.Conn, payload []byte) error {
	var hdr [4]byte
	binary.BigEndian.PutUint32(hdr[:], uint32(len(payload)))
	if _, err := conn.Write(hdr[:]); err != nil {
		return err
	}
	_, err := conn.Write(payload)
	return err
}

func readN(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func readFrame(conn net.Conn) ([]byte, error) {
	hdr, err := readN(conn, 4)
	if err != nil {
		return nil, err
	}
	l := binary.BigEndian.Uint32(hdr)
	if l == 0 {
		return []byte{}, nil
	}
	return readN(conn, int(l))
}

// ---------- helpers ----------
func encodeString(b *bytes.Buffer, s string) {
	_ = binary.Write(b, binary.BigEndian, uint16(len(s)))
	_, _ = b.WriteString(s)
}

func encodeBetFields(b *bytes.Buffer, bet *Bet) {
	_ = binary.Write(b, binary.BigEndian, int32(atoiSafe(bet.Agency)))
	encodeString(b, bet.FirstName)
	encodeString(b, bet.LastName)
	encodeString(b, bet.Document)
	encodeString(b, bet.Birthdate)
	_ = binary.Write(b, binary.BigEndian, int32(atoiSafe(bet.Number)))
}

// ---------- batch ----------
func SendBatch(conn net.Conn, bets []*Bet) error {
	var p bytes.Buffer
	p.WriteString(magicBCH0)
	n := uint16(len(bets))
	_ = binary.Write(&p, binary.BigEndian, n)
	for _, bet := range bets {
		encodeBetFields(&p, bet)
	}
	return writeFrame(conn, p.Bytes())
}

func ReadAck(conn net.Conn) (ok bool, count uint16, err error) {
	f, e := readFrame(conn)
	if e != nil {
		return false, 0, e
	}
	if len(f) < 4+1+2 || string(f[:4]) != magicACK0 {
		return false, 0, errors.New("bad ACK0")
	}
	pos := 4
	ok = f[pos] == 1
	pos++
	count = binary.BigEndian.Uint16(f[pos : pos+2])
	return ok, count, nil
}

func betPayloadSize(b *Bet) int {
	// agency(int32) + number(int32)
	const fixedInts = 4 + 4

	// Each string is encoded as: uint16 length + raw bytes
	strFieldSize := func(s string) int { return 2 + len(s) }

	return fixedInts +
		strFieldSize(b.FirstName) +
		strFieldSize(b.LastName) +
		strFieldSize(b.Document) +
		strFieldSize(b.Birthdate)
}

func FrameSizeForBatch(bets []*Bet) int {
	const (
		frameLen = 4
		// payload fixed header: "BCH0"(4) + count(uint16)(2)
		payloadHeader = 4 + 2
	)

	size := frameLen + payloadHeader
	for _, b := range bets {
		size += betPayloadSize(b)
	}
	return size
}
