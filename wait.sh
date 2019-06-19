#!/bin/sh

is_ready() {
    eval "$WAIT_COMMAND"
}

# wait until is ready
i=0
while ! is_ready; do
    i=`expr $i + 1`
    if [[ $i -ge $WAIT_LOOPS ]]; then
        echo "[$(date '+%Y-%m-%d %H-%M-%S %Z')] [$0] [ERROR] Dependencies not ready, shutting down"
        exit 1
    fi
    echo "[$(date '+%Y-%m-%d %H-%M-%S %Z')] [$0] [INFO] Waiting for dependencies"
    sleep $WAIT_SLEEP
done

#start the script
exec $WAIT_START_CMD
