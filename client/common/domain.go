package common

import (
	"bufio"
	"encoding/csv"
	"fmt"
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

func LoadBetsFromCSV(path string, agencyID string) ([]*Bet, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("no se pudo abrir %s: %w", path, err)
	}
	defer f.Close()

	r := csv.NewReader(bufio.NewReader(f))
	r.TrimLeadingSpace = true
	records, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("error leyendo CSV %s: %w", path, err)
	}

	bets := make([]*Bet, 0, len(records))
	for _, rec := range records {
		// saltar filas vacías
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
		b, err := betFromCSVRow(agencyID, rec)
		if err != nil {
			return nil, err
		}
		bets = append(bets, b)
	}
	return bets, nil
}
