#!/usr/bin/env bash

MDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

cd $MDIR
cat $1.genv
