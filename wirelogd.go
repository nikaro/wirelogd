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
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/samber/lo"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.zx2c4.com/wireguard/wgctrl"
)

type wirelogdConfig struct {
	ConfigFile string `json:"config_file"`
	Debug      bool   `json:"debug"`
	Refresh    int    `json:"refresh"`
	Timeout    int64  `json:"timeout"`
}

type wirelogdPeer struct {
	Interface       string `json:"interface"`
	PublicKey       string `json:"public_key"`
	Endpoint        string `json:"endpoint"`
	AllowedIPs      string `json:"allowed_ips"`
	LatestHandshake int64  `json:"-"`
}

func (p *wirelogdPeer) JSON() []byte {
	pJSON, err := json.Marshal(p)
	if err != nil {
		log.Error().Err(err).Send()
		os.Exit(1)
	}

	return pJSON
}

var rootCmd = &cobra.Command{
	Use:               "wirelogd",
	Short:             "Wirelogd is a logging daemon for WireGuard.",
	Long:              ``,
	Run:               runLoop,
	DisableAutoGenTag: true,
}
var config *wirelogdConfig

func init() {
	cobra.OnInitialize(initConfig)

	// set command flags
	rootCmd.Flags().StringP("config", "c", "", "path to configuration file")
	rootCmd.Flags().BoolP("debug", "d", false, "enable debug logging")
	rootCmd.Flags().IntP("refresh", "r", 0, "refresh interval in seconds")
	rootCmd.Flags().IntP("timeout", "t", 0, "wireguard handshake timeout in seconds")

	// bind command flags
	if err := viper.BindPFlags(rootCmd.Flags()); err != nil {
		log.Error().Err(err).Send()
	}
}

func initConfig() {
	// set defaults
	viper.SetDefault("debug", false)
	viper.SetDefault("refresh", 5)
	viper.SetDefault("timeout", 300)

	// bind environment variables
	viper.SetEnvPrefix("wirelogd")
	viper.AutomaticEnv()
	if err := viper.BindEnv("config"); err != nil {
		log.Error().Err(err).Send()
	}

	// set config file path
	if rootCmd.Flag("config").Value.String() != "" {
		viper.SetConfigFile(rootCmd.Flag("config").Value.String())
	} else if viper.GetString("config") != "" {
		viper.SetConfigFile(viper.GetString("config"))
	} else {
		viper.SetConfigName("config")
		viper.AddConfigPath("/etc/wirelogd")
	}

	// read config
	if err := viper.ReadInConfig(); err != nil {
		log.Warn().Err(err).Send()
	}

	// set global config
	config = &wirelogdConfig{
		ConfigFile: viper.ConfigFileUsed(),
		Debug:      viper.GetBool("debug"),
		Refresh:    viper.GetInt("refresh"),
		Timeout:    viper.GetInt64("timeout"),
	}

	// set global log level
	logLevel := lo.Ternary[zerolog.Level](config.Debug, zerolog.DebugLevel, zerolog.InfoLevel)
	zerolog.SetGlobalLevel(logLevel)
}

func getPeers() []wirelogdPeer {
	wg, err := wgctrl.New()
	if err != nil {
		log.Error().Err(err).Send()
		os.Exit(1)
	}
	defer wg.Close()

	wgDevices, err := wg.Devices()
	if err != nil {
		log.Error().Err(err).Send()
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

			// replace empty allowed ips
			var allowedIPs string
			if len(wgPeer.AllowedIPs) > 0 {
				allowedIPs = wgPeer.AllowedIPs[0].IP.String()
			} else {
				allowedIPs = "(none)"
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

func runLoop(cmd *cobra.Command, args []string) {
	configJSON, _ := json.Marshal(config)
	log.Debug().RawJSON("config", configJSON).Send()

	log.Info().Msg("start wirelogd")

	// catch sigterm signal
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		log.Info().Msg("stop wirelogd")
		os.Exit(0)
	}()

	// init activity state
	activityState := make(map[string]bool)

	for {
		wgPeers := getPeers()
		peersJSON, _ := json.Marshal(wgPeers)
		log.Debug().RawJSON("peers", peersJSON).Send()

		now := time.Now().Unix()
		for _, wgPeer := range wgPeers {
			wgKey := fmt.Sprintf("%s-%s", wgPeer.Interface, wgPeer.PublicKey)
			wasActive := activityState[wgKey]
			timedOut := (now - wgPeer.LatestHandshake) > config.Timeout
			if wasActive && timedOut {
				activityState[wgKey] = false
				log.Info().RawJSON("peer", wgPeer.JSON()).Str("state", "inactive").Send()
			} else if !wasActive && !timedOut {
				activityState[wgKey] = true
				log.Info().RawJSON("peer", wgPeer.JSON()).Str("state", "active").Send()
			}
		}

		// wait
		time.Sleep(time.Duration(config.Refresh) * time.Second)
	}
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		log.Error().Err(err).Send()
		os.Exit(1)
	}
}
