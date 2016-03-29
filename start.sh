#!/bin/sh

exec 2>&1
GUNICORN=/usr/bin/gunicorn
ROOT=$(PWD)
PID=/var/run/gunicorn.pid
APP=driver:app

if [ -f $PID ]; then rm $PID; fi

$GUNICORN -u root --chdir $ROOT --pid=$PID \
-b unix:///run/docker/plugins/daolinet.sock $APP \
--timeout=5 \
--log-level=debug \
--workers 1 \
