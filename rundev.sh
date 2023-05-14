#!/bin/sh

# ./runstests.sh [--version <python version>] [arguments for pytest]

version="3.7"
for a
do
  shift
  if [ "$prev" == "--version" ]
  then
    version="$a"
    prev=""
  else
    case $a in
      --version) prev="$a";;
      *) set -- "$@" "$a";;
    esac
  fi
done

version_dash=`echo $version | sed 's/\./-/'`

BASE_PYTHON_VERSION=$version DASH_PYTHON_VERSION=$version_dash BASE_NODE_VERSION=18 \
BUILDKIT_PROGRESS=plain docker compose -f compose-dev.yaml up $@
