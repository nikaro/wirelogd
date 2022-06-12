#!/bin/sh
set -e

case "$1" in
    configure)
        systemctl daemon-reload
        if [ -z "$2" ]; then
            if ! getent passwd wirelogd >>/dev/null 2>&1 ; then
                useradd --home-dir /var/run/wirelogd --shell /usr/sbin/nologin --system --user-group wirelogd
                if command -v setfacl >>/dev/null 2>&1 ; then
                    setfacl -m u:wirelogd:rX,g:wirelogd:rX /etc/wireguard
                fi
            fi
            systemctl enable --now wirelogd.service
        fi
    ;;
    *)
    ;;
esac
