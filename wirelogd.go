// Wirelogd is a logging daemon for WireGuard.
//
// Since WireGuard itself does not log the state of its peers (and since it is
// UDP based so, there no concept of "connection state"), Wirelogd relies on
// the latest handshake to determine if a peer is active or inactive. While
// there is traffic the handshake should be renewed every 2 minutes. If there is
// no traffic, handshake is not renewed. Based on this behavior we assume that
// if there is no new handshake after a while (default Wirelogd timeout value
// is 5 minutes), the client is probably inactive.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"log/syslog"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"golang.zx2c4.com/wireguard/wgctrl"
)

type wirelogdConfig struct {
	Debug          bool   `json:"debug"`
	LogDestination string `json:"log_destination"`
	LogFormat      string `json:"log_format"`
	Refresh        int    `json:"refresh"`
	Timeout        int64  `json:"timeout"`
}

type wirelogdPeer struct {
	Interface       string   `json:"interface"`
	PublicKey       string   `json:"public_key"`
	Endpoint        string   `json:"endpoint"`
	AllowedIPs      []string `json:"allowed_ips"`
	LatestHandshake int64    `json:"-"`
}

var configFile string
var config wirelogdConfig
var version string
var showVersion bool

func init() {
	// Set default values
	config = wirelogdConfig{
		Debug:          false,
		LogDestination: "stdout",
		LogFormat:      "json",
		Refresh:        5,
		Timeout:        300,
	}

	// Parse flags
	var configFromArgs wirelogdConfig
	flag.StringVar(&configFile, "config", "", "path to JSON configuration file")
	flag.StringVar(&configFromArgs.LogDestination, "log-destination", "stdout", "logging destination, could be \"stdout\", \"syslog\" or a file path")
	flag.StringVar(&configFromArgs.LogFormat, "log-format", "json", "logging format, could be \"json\" or \"text\"")
	flag.BoolVar(&configFromArgs.Debug, "debug", false, "enable debug logging")
	flag.IntVar(&configFromArgs.Refresh, "refresh", 0, "refresh interval in seconds")
	flag.Int64Var(&configFromArgs.Timeout, "timeout", 0, "wireguard handshake timeout in seconds")
	flag.BoolVar(&showVersion, "version", false, "show version")
	flag.Parse()

	// Read config file
	if configFile != "" {
		if data, errRead := os.ReadFile(configFile); errRead == nil {
			if errParse := json.Unmarshal(data, &config); errParse != nil {
				panic(fmt.Sprintf("cannot parse configuration file: %s", errParse.Error()))
			}
		} else {
			panic(fmt.Sprintf("cannot read configuration file: %s", errRead.Error()))
		}
	}

	// Apply config from flags
	if isFlagPassed("debug") {
		config.Debug = configFromArgs.Debug
	}
	if isFlagPassed("log-destination") {
		config.LogDestination = configFromArgs.LogDestination
	}
	if isFlagPassed("log-format") {
		config.LogFormat = configFromArgs.LogFormat
	}
	if isFlagPassed("refresh") {
		config.Refresh = configFromArgs.Refresh
	}
	if isFlagPassed("timeout") {
		config.Timeout = configFromArgs.Timeout
	}

	// Configure logging level
	logHandlerOptions := &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}
	if config.Debug {
		logHandlerOptions.Level = slog.LevelDebug
	}
	// Configure logging destination
	var logWriter io.Writer
	switch config.LogDestination {
	case "stdout":
		logWriter = os.Stdout
	case "syslog":
		syslogPriority := syslog.LOG_INFO
		if config.Debug {
			syslogPriority = syslog.LOG_DEBUG
		}
		if syslogWriter, syslogErr := syslog.New(syslogPriority, "wirelogd"); syslogErr == nil {
			logWriter = syslogWriter
		} else {
			panic(syslogErr.Error())
		}
	default:
		if logFile, logFileErr := os.OpenFile(config.LogDestination, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644); logFileErr == nil {
			logWriter = logFile
		} else {
			panic(logFileErr.Error())
		}
	}
	// Configure logging format
	var logHandler slog.Handler
	switch config.LogFormat {
	case "json":
		logHandler = slog.NewJSONHandler(logWriter, logHandlerOptions)
	case "text":
		logHandler = slog.NewTextHandler(logWriter, logHandlerOptions)
	default:
		panic("unsupported log format")
	}
	// Configure logger
	logger := slog.New(logHandler)
	slog.SetDefault(logger)
}

func (p *wirelogdPeer) JSON() []byte {
	pJSON, err := json.Marshal(p)
	if err != nil {
		slog.Error(err.Error())
		os.Exit(1)
	}

	return pJSON
}

func getPeers() []wirelogdPeer {
	wg, err := wgctrl.New()
	if err != nil {
		slog.Error(err.Error())
		os.Exit(1)
	}
	defer func() {
		if err := wg.Close(); err != nil {
			slog.Error(err.Error())
		}
	}()

	wgDevices, err := wg.Devices()
	if err != nil {
		slog.Error(err.Error())
		os.Exit(1)
	}

	var wgPeers []wirelogdPeer
	for _, wgDevice := range wgDevices {
		for _, wgPeer := range wgDevice.Peers {
			// replace empty endpoint
			var endpoint string
			if wgPeer.Endpoint != (*net.UDPAddr)(nil) {
				endpoint = fmt.Sprintf("%s:%d", wgPeer.Endpoint.IP.String(), wgPeer.Endpoint.Port)
			} else {
				endpoint = "(none)"
			}

			// get list of allowed ip addresses
			var allowedIPs []string
			for _, allowedIp := range wgPeer.AllowedIPs {
				allowedIPs = append(allowedIPs, allowedIp.IP.String())
			}

			wgPeers = append(wgPeers, wirelogdPeer{
				Interface:       wgDevice.Name,
				PublicKey:       wgPeer.PublicKey.String(),
				Endpoint:        endpoint,
				AllowedIPs:      allowedIPs,
				LatestHandshake: wgPeer.LastHandshakeTime.Unix(),
			})
		}
	}

	return wgPeers
}

func main() {
	configJSON, _ := json.Marshal(config)
	slog.Debug("", slog.String("config", string(configJSON)))

	if showVersion {
		fmt.Printf("wirelogd version %s\n", version)
		os.Exit(0)
	}

	slog.Info("start wirelogd")

	// catch sigterm signal
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		slog.Info("stop wirelogd")
		os.Exit(0)
	}()

	// init activity state
	activityState := make(map[string]bool)

	for {
		wgPeers := getPeers()

		peersJSON, _ := json.Marshal(wgPeers)
		slog.Debug("", slog.String("peers", string(peersJSON)))

		now := time.Now().Unix()
		for _, wgPeer := range wgPeers {
			wgKey := fmt.Sprintf("%s-%s", wgPeer.Interface, wgPeer.PublicKey)
			wasActive := activityState[wgKey]
			timedOut := (now - wgPeer.LatestHandshake) > config.Timeout
			if wasActive && timedOut {
				activityState[wgKey] = false
				slog.Info("", slog.String("peer", string(wgPeer.JSON())), slog.String("state", "inactive"))
			} else if !wasActive && !timedOut {
				activityState[wgKey] = true
				slog.Info("", slog.String("peer", string(wgPeer.JSON())), slog.String("state", "active"))
			}
		}

		// wait
		time.Sleep(time.Duration(config.Refresh) * time.Second)
	}
}
