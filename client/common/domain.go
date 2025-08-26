package common

import (
	"fmt"
	"os"
)

type Bet struct {
	Agency    string `json:"agency"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
	Document  string `json:"document"`
	Birthdate string `json:"birthdate"`
	Number    string `json:"number"`
}

func LoadBetFromEnv(agencyID string) (*Bet, error) {
	firstName := os.Getenv("NOMBRE")
	lastName := os.Getenv("APELLIDO")
	document := os.Getenv("DOCUMENTO")
	birthdate := os.Getenv("NACIMIENTO")
	number := os.Getenv("NUMERO")

	if firstName == "" || lastName == "" || document == "" || birthdate == "" || number == "" {
		return nil, fmt.Errorf("faltan variables de entorno obligatorias (NOMBRE/APELLIDO/DOCUMENTO/NACIMIENTO/NUMERO)")
	}

	return &Bet{
		Agency:    agencyID,
		FirstName: firstName,
		LastName:  lastName,
		Document:  document,
		Birthdate: birthdate,
		Number:    number,
	}, nil
}
