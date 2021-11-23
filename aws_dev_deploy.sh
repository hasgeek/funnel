#!/bin/bash
set -e
echo 'Starting to Deploy...'
ssh ec2-user@3.144.184.165 "
		docker image prune -f 
        cd funnel
        docker-compose down
        git fetch origin
        git reset --hard origin/aws  &&  echo 'git fetched and hard reset'
        docker-compose build 
        docker run vivekdurai/funnel flask db upgrade
        docker-compose up -d
        "
echo 'Deployed to staging without db update successfully'