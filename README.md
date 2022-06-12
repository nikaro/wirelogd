# Wirelogd

> :warning: Wirelogd has been rewritten in Go, you can still found the old
> Python version in `python` branch.
>
> [More information...](https://github.com/nikaro/wirelogd/wiki/Rewrite-in-Go)

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
Wirelogd is a logging daemon for WireGuard.

Usage:
  wirelogd [flags]

Flags:
  -c, --config string   path to configuration file
  -d, --debug           enable debug logging
  -h, --help            help for wirelogd
  -r, --refresh int     refresh interval in seconds
  -t, --timeout int     wireguard handshake timeout in seconds
```

## Installation

### Manual

```
$ git clone <repo-url> <dest-path>
$ cd <dest-path>
$ make
$ sudo make PREFIX=/usr install
$ sudo mkdir -p /etc/wirelogd
$ sudo cp /usr/share/wirelogd/config.toml /etc/wirelogd
$ sudo cp /usr/share/wirelogd/wirelogd-nopasswd /etc/sudoers.d/
$ sudo cp /usr/share/wirelogd/wirelogd.service /etc/systemd/system/
$ sudo useradd --home-dir /var/run/wirelogd --shell /usr/sbin/nologin --system --user-group wirelogd
$ sudo systemctl daemon-reload
$ sudo systemctl enable --now wirelogd.service
```

## Configuration

By default Wirelogd will look for its configuration in
`/etc/wirelogd/config.toml`, you can override this by using `--config/-c`
command-line argument or by specifying a `WIRELOGD_CONFIG` variable in your
environment. Wirelogd will fallback on its hard-coded defaults if no
configuration is specified.

Here is an exemple configuration file, with the default values:

```toml
debug = false
refresh = 5
timeout = 300
```

Here are the environment variables available:

- `WIRELOGD_CONFIG`
- `WIRELOGD_DEBUG`
- `WIRELOGD_REFRESH`
- `WIRELOGD_TIMEOUT`

Configuration precedence is, by lowest (most easily overridden) to highest
(overrides all others):

- hard-coded defaults
- `/etc/wirelogd/config.toml` or given configuration file (by env or args)
- environment variables
- command-line arguments
