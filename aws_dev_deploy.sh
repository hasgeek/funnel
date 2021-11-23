#!/bin/bash
echo 'Starting to Deploy...'
ssh -o StrictHostKeyChecking=no ec2-user@ec2-3-144-184-165.us-east-2.compute.amazonaws.com " docker image prune -f 
        cd funnel
        docker-compose down
        git fetch origin
        git reset --hard origin/develop  &&  echo 'git fetched and hard reset'
        docker-compose build 
        docker exec -it web flask db upgrade
        docker-compose up -d
        "
echo 'Deployed to staging without db update successfully'