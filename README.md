# Wirelogd

Wirelogd is a logging daemon for WireGuard. Since WireGuard itself does not log
the state of its peers (and since it is UDP based so, there no concept of
"connection state"), Wirelogd relies on the latest handshake to determine if a
peer is active or inactive. While there is trafic the handshake should be
renewed every 2 minutes. If there is no trafic, handshake is not renewed. Based
on this behavior we assume that if there is no new handshake after a while
(default Wirelogd timeout value is 5 minutes), the client is probably inactive.

Output in journalctl will look like this:

```
# journalctl -t wirelogd -f
juin 12 15:19:12 hostname wirelogd[15233]: INFO - starting wirelodg
#juin 12 15:19:37 hostname wirelogd[15233]: INFO - <wg-gen-web-user> - <public-key> - <endpoint-aka-public-ip> - <allowed-ips-aka-tunnel-ips> - <interface> - <state>#
juin 12 15:19:37 hostname wirelogd[15233]: INFO - unknown - NRCIeq4a/vChupjDlomdYZyJgmPxrYZsHmxWx4Z409A= - 149.215.14.193:42967 - 10.6.6.2/32 - wg0 - active
juin 12 15:26:38 hostname wirelogd[15233]: INFO - unknown - NRCIeq4a/vChupjDlomdYZyJgmPxrYZsHmxWx4Z409A= - 149.215.14.193:42967 - 10.6.6.2/32 - wg0 - inactive
```

## Usage

```
# wirelogd -h
usage: wirelogd [-h] [--config PATH] [--debug] [--refresh SEC] [--sudo]
                [--timeout SEC] [--wg-gen-web] [--wg-gen-web-path]

WireGuard logging.

optional arguments:
  -h, --help            show this help message and exit
  --config str, -c str  path to configuration file
  --debug, -d           enable debug logging
  --refresh int, -r int
                        refresh interval in seconds
  --sudo, -s            run subprocess commands with sudo
  --timeout int, -t int
                        wireguard handshake timeout in seconds
  --wg-gen-web, -w      link peer with its wg-gen-web config name
  --wg-gen-web-path     path where wg-gen-web store its config files
```

## Installation

### deb package

```
# git clone <repo-url> <dest-path>
# cd <dest-path>
# make deb
# dpkg -i dist/wirelogd-<version>.deb
```

### Manual

```
# git clone <repo-url> <dest-path>
# cd <dest-path>
# make PREFIX=/usr install
# cp contrib/wirelogd.cfg /etc/
# cp contrib/wirelogd-nopasswd /etc/sudoers.d/
# cp contrib/wirelogd.service /etc/systemd/system/
# useradd --home-dir /var/run/wirelogd --shell /usr/sbin/nologin --system --user-group wirelogd
# setfacl -m u:wirelogd:rX /etc/wireguard
# systemctl daemon-reload
# systemctl enable --now wirelogd.service
```

## Configuration

By default Wirelogd will look for its configuration in `/etc/wirelogd.cfg`, you can override this by using `--config/-c` command-line argument or by specifying a `WIRELOGD_CONFIG` variable in your environment. Wirelogd will fallback on its hard-coded defaults if no configuration is specified.

Here is an exemple configuration file, with the default values:

```ini
[wirelogd]
debug = no
refresh = 5
sudo = no
timeout = 300
wg-gen-web = no
wg-gen-web-path = /etc/wireguard/
```

Here are the environment variables available:

- `WIRELOGD_CONFIG`
- `WIRELOGD_DEBUG`
- `WIRELOGD_REFRESH`
- `WIRELOGD_SUDO`
- `WIRELOGD_TIMEOUT`
- `WIRELOGD_WG_GEN_WEB`
- `WIRELOGD_WG_GEN_WEB_PATH`

Configuration precedence is, by lowest (most easily overridden) to highest (overrides all others):

- hard-coded defaults
- `/etc/wirelogd.cfg` or given configuration file (by env or args)
- environment variables
- command-line arguments

## wg-gen-web

[wg-gen-web](https://github.com/vx3r/wg-gen-web) is a simple web based configuration generator for WireGuard.

Its usage with Wirelogd is optional. It used just to be able to log the name given into wg-gen-web to peer, this way it is easier to know to which user belong a public key.
