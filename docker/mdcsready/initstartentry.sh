#!/bin/bash
#
# set -e

[ "$INITBIN" = "" ] && export INITBIN=/usr/local/sbin

init=$INITBIN/mongo_init_users.sh
ctl=$INITBIN/mongod_ctl.sh

[ "$1" = "" ] && exit 0

case "$1" in
    init)
        $init
        ;;
    initstart)
        $init && $ctl start
        ;;
    start)
        $ctl start
        ;;
    stop)
        $ctl stop
        ;;
    status)
        $ctl status
        ;;
    null)
        ;;
    *)
        echo Usage: $0 init\|initstart\|start\|stop\|status
        exit 1
        ;;
esac

shift
if [ "$1" != "" ]; then
    exec "$@"
fi

