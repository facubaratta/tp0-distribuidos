package main

import (
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/op/go-logging"
	"github.com/pkg/errors"
	"github.com/spf13/viper"

	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/common"
)

var log = logging.MustGetLogger("log")

// InitConfig: lee config.yaml y variables de entorno (CLI_*).
func InitConfig() (*viper.Viper, error) {
	v := viper.New()

	v.AutomaticEnv()
	v.SetEnvPrefix("cli")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	v.BindEnv("id")
	v.BindEnv("server", "address")
	v.BindEnv("loop", "period")
	v.BindEnv("loop", "amount")
	v.BindEnv("log", "level")

	v.BindEnv("data", "dir")        // CLI_DATA_DIR
	v.BindEnv("batch", "maxAmount") // CLI_BATCH_MAXAMOUNT
	v.BindEnv("batch", "maxBytes")  // CLI_BATCH_MAXBYTES

	// Defaults
	v.SetDefault("data.dir", "/data")
	v.SetDefault("batch.maxAmount", 50)
	v.SetDefault("batch.maxBytes", 8*1024) // 8KB por consigna

	v.SetConfigFile("./config.yaml")
	if err := v.ReadInConfig(); err != nil {
		fmt.Printf("Configuration could not be read from config file. Using env variables instead")
	}

	if _, err := time.ParseDuration(v.GetString("loop.period")); err != nil {
		return nil, errors.Wrapf(err, "Could not parse CLI_LOOP_PERIOD env var as time.Duration.")
	}

	return v, nil
}

func InitLogger(logLevel string) error {
	baseBackend := logging.NewLogBackend(os.Stdout, "", 0)
	format := logging.MustStringFormatter(`%{time:2006-01-02 15:04:05} %{level:.5s}     %{message}`)
	backendFormatter := logging.NewBackendFormatter(baseBackend, format)
	backendLeveled := logging.AddModuleLevel(backendFormatter)
	logLevelCode, err := logging.LogLevel(logLevel)
	if err != nil {
		return err
	}
	backendLeveled.SetLevel(logLevelCode, "")
	logging.SetBackend(backendLeveled)
	return nil
}

func PrintConfig(v *viper.Viper) {
	log.Infof(
		"action: config | result: success | client_id: %s | server_address: %s | loop_amount: %v | loop_period: %v | log_level: %s | data_dir: %s | batch_max_amount: %d | batch_max_bytes: %d",
		v.GetString("id"),
		v.GetString("server.address"),
		v.GetInt("loop.amount"),
		v.GetDuration("loop.period"),
		v.GetString("log.level"),
		v.GetString("data.dir"),
		v.GetInt("batch.maxAmount"),
		v.GetInt("batch.maxBytes"),
	)
}

func main() {
	v, err := InitConfig()
	if err != nil {
		log.Criticalf("%s", err)
	}

	if err := InitLogger(v.GetString("log.level")); err != nil {
		log.Criticalf("%s", err)
	}

	PrintConfig(v)

	id := v.GetString("id")
	batchMax := v.GetInt("batch.maxAmount")
	maxBytes := v.GetInt("batch.maxBytes")
	dataDir := v.GetString("data.dir")

	allBets, err := common.LoadBetsFromCSV(dataDir, id)
	if err != nil {
		log.Criticalf("action: load_bets | result: fail | client_id: %v | error: %v", id, err)
		return
	}

	clientConfig := common.ClientConfig{
		ServerAddress: v.GetString("server.address"),
		ID:            id,
		LoopAmount:    v.GetInt("loop.amount"),
		LoopPeriod:    v.GetDuration("loop.period"),
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM)

	client := common.NewClient(clientConfig)
	client.StartClientLoop(sigChan, allBets, batchMax, maxBytes)
}
