package common

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strings"
)

type Bet struct {
	Agency    string `json:"agency"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
	Document  string `json:"document"`
	Birthdate string `json:"birthdate"`
	Number    string `json:"number"`
}

func betFromCSVRow(agencyID string, row []string) (*Bet, error) {
	if len(row) < 5 {
		return nil, fmt.Errorf("fila CSV inválida (esperado 5 campos): %v", row)
	}
	norm := func(s string) string { return strings.TrimSpace(s) }
	return &Bet{
		Agency:    agencyID,
		FirstName: norm(row[0]),
		LastName:  norm(row[1]),
		Document:  norm(row[2]),
		Birthdate: norm(row[3]), // YYYY-MM-DD
		Number:    norm(row[4]),
	}, nil
}

type BetSource interface {
	Next() (*Bet, error)
	Close() error
}

type CSVBetIterator struct {
	f        *os.File
	r        *csv.Reader
	agencyID string
}

func NewCSVBetIterator(path, agencyID string) (*CSVBetIterator, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("no se pudo abrir %s: %w", path, err)
	}
	r := csv.NewReader(bufio.NewReader(f))
	r.TrimLeadingSpace = true
	return &CSVBetIterator{f: f, r: r, agencyID: agencyID}, nil
}

func (it *CSVBetIterator) Next() (*Bet, error) {
	for {
		rec, err := it.r.Read()
		if err != nil {
			if err == io.EOF {
				return nil, io.EOF
			}
			return nil, fmt.Errorf("error leyendo CSV: %w", err)
		}
		// skip empty rows
		allEmpty := true
		for _, c := range rec {
			if strings.TrimSpace(c) != "" {
				allEmpty = false
				break
			}
		}
		if allEmpty {
			continue
		}
		return betFromCSVRow(it.agencyID, rec)
	}
}

func (it *CSVBetIterator) Close() error { return it.f.Close() }
