#!/bin/sh

## Kill both with control-c
## From: https://superuser.com/questions/1118204/how-to-use-ctrlc-to-kill-all-background-processes-started-in-a-bash-script/1118226
## Use INT not SIGINT
## From: https://unix.stackexchange.com/questions/314554/why-do-i-get-an-error-message-when-trying-to-trap-a-sigint-signal
trap 'kill $BGPID; exit' INT
python3 server.py &
BGPID=$!
## Serve the whole repository, since the in-browser (Pyodide) computation loads the Python files.
python3 -m http.server --directory ..
