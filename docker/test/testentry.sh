#!/bin/bash
#
[ "$MDCS" = "" ] && export MDCS=/mdcs
[ "$INITBIN" = "" ] && export INITBIN=/usr/local/sbin
[ "$INITETC" = "" ] && export INITETC=/usr/local/etc

function start {
    echo mongod --dbpath=/tmp/mongodb/db --logpath=/tmp/mongodb/logs/mongod.log \
           --noauth --fork
    mongod --dbpath=/tmp/mongodb/db --logpath=/tmp/mongodb/logs/mongod.log \
           --noauth --fork
}

cd /mdcs

case "$1" in
    startdb)
        start
        ;;
    testall)
        start && xmltemplate/tests/runalltests.py
        ;;
    null)
        ;;
    *)
        echo Usage:  `basename $0` startdb\|null
        exit 1
        ;;
esac
             
shift
if [ "$1" != "" ]; then
    # echo "$@"
    exec "$@"
fi

