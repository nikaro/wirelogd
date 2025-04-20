# Wirelogd

Wirelogd is a logging daemon for WireGuard. Since WireGuard itself does not log
the state of its peers (and since it is UDP based so there is no concept of
"connection state"), Wirelogd relies on the latest handshake to determine if a
peer is active or inactive. While there is trafic the handshake should be
renewed every 2 minutes. If there is no trafic handshake is not renewed. Based
on this behavior we assume that if there is no new handshake after a while
(default Wirelogd timeout value is 5 minutes), the client is probably inactive.

Output in journalctl will look like this:

```
# journalctl -t wirelogd -f
juin 12 15:19:12 hostname wirelogd[15233]: {"level":"info","time":"2022-06-12T11:29:25+02:00","message":"start wirelogd"}
juin 12 15:19:37 hostname wirelogd[15233]: {"level":"info","peer":{"interface":"wg0","public_key":"xr4lhgUWOQHTWf5rYTr2Ia0710xsCNaKAl8PtNTp3TQ=","endpoint":"203.0.113.162:57891","allowed_ips":"192.0.2.119"},"state":"active","time":"2022-06-12T11:28:01+02:00"}
```

## Usage

```
# wirelogd -h
Usage of ./build/wirelogd-darwin-arm64:
  -config string
        path to JSON configuration file
  -debug
        enable debug logging
  -log-destination string
        logging destination, could be "stdout", "syslog" or a file path (default "stdout")
  -log-format string
        logging format, could be "json" or "text" (default "json")
  -refresh int
        refresh interval in seconds
  -timeout int
        wireguard handshake timeout in seconds
```

## Installation

### Sources

```
$ git clone <repo-url> <dest-path>
$ cd <dest-path>
$ make
$ sudo task install
$ sudo mkdir -p /etc/wirelogd
$ sudo cp /usr/local/share/wirelogd/config.json /etc/wirelogd
$ sudo cp /usr/local/share/wirelogd/wirelogd.service /etc/systemd/system/
$ sudo useradd --home-dir /var/run/wirelogd --shell /usr/sbin/nologin --system --user-group wirelogd
$ sudo setfacl -m u:wirelogd:rX,g:wirelogd:rX /etc/wireguard
$ sudo systemctl daemon-reload
$ sudo systemctl enable --now wirelogd.service
```

## Configuration

Wirelogd can take a JSON configuration file via the `-config` command-line flag.

Here is an exemple configuration file, with the default values:

```json
{
  "debug": false,
  "log_destination": "stdout",
  "log_format": "json",
  "refresh": 5,
  "timeout": 300
}
```

Configuration precedence is, by lowest (most easily overridden) to highest
(overrides all others):

- hard-coded defaults
- configuration file
- command-line arguments
