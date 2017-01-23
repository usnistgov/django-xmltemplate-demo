#!/bin/bash
#
[ "$MDCS" = "" ] && export MDCS=/mdcs
[ "$INITBIN" = "" ] && export INITBIN=/usr/local/sbin
[ "$INITETC" = "" ] && export INITETC=/usr/local/etc

ctl=$INITBIN/mongd_ctl.sh
function initmongodb { $INITBIN/initstartentry.sh init; }

function faketty { script -qfc "$(printf "%q " "$@")" /dev/null; }

function initmdcs {
    if [ -f "$MDCS/mgi/settings.py" ]; then
        $INITBIN/mongod_ctl.sh start && sleep 1
        cp $INITETC/settings.py $MDCS/mgi
        cd $MDCS
        python manage.py migrate
        source $INITETC/superuser.inputs
        echo python manage.py createsuperuser --noinput --username $SU_USERNAME \
               --email $SU_EMAIL
        python manage.py createsuperuser --noinput --username $SU_USERNAME \
               --email $SU_EMAIL
        echo python $INITETC/setsupw.py '<pw>'
        PYTHONPATH=$MDCS python $INITETC/setsupw.py $SU_PW
    else
        echo MDCS app code not found: $MDCS/mgi/settings.py
        false
    fi
}

function startmdcs {
    $INITBIN/mongod_ctl.sh start
    cd $MDCS 
    exec python manage.py runserver 0.0.0.0:80 | tee -a /data/mdcs.log
}

case "$1" in
    initdb)
        initmongodb
        ;;
    init)
        initmongodb && initmdcs
        ;;
    initstart)
        initmongodb && initmdcs && startmdcs
        ;;
    start)
        startmdcs
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
        echo Usage: `basename $0` init\|initstart\|start\|stop\|status
        exit 1
        ;;
esac

shift
if [ "$1" != "" ]; then
    # echo "$@"
    exec "$@"
fi
