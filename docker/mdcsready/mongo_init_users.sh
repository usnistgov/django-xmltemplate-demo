#!/bin/bash
#
set -e
# set -x
MONGOD_CMD="mongod --config=/etc/mongod.conf --fork"
initetc=${INITETC:=/usr/local/etc}

function start {
    echo $MONGOD_CMD $@ 1>&2
    $MONGOD_CMD $@ | grep "forked process:" | sed -e 's/^.*: //'
}

# start mongo server without authentication to set the admin account
pid=`start --noauth`
sleep 1

# set the admin account
mongo admin $initetc/create_admin.js 

# restart the server with authentication
kill $pid
sleep 1
pid=`start`
echo $pid > /data/mongod.pid
sleep 1

mongo -u admin -p mdcs4odi --authenticationDatabase admin mgidata $initetc/create_mgiuser.js
mongo -u admin -p mdcs4odi --authenticationDatabase admin mgitest $initetc/create_mgiuser.js
kill $pid
sleep 1

echo MongoDB initialized | tee -a /data/mdcsstatus.txt
