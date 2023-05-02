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

docker image inspect hasgeek/funnel:python-$version-node-18 --format "Found hasgeek/funnel:python-$version-node-18" || make build-$version
docker image inspect funnel-test-base:python-$version-node-18 --format "Found funnel-test-base:python-$version-node-18" || make build-test-base-$version

BASE_PYTHON_VERSION=$version DASH_PYTHON_VERSION=$version_dash BASE_NODE_VERSION=18 \
docker compose -f docker-compose-test.yml run --rm -e PWD=/home/funnel/app funnel-test $@
BASE_PYTHON_VERSION=$version DASH_PYTHON_VERSION=$version_dash BASE_NODE_VERSION=18 \
docker compose -f docker-compose-test.yml down
