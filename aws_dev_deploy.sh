#!/bin/bash
echo 'Starting to Deploy...'
ssh ec2-user@ec2-3-144-184-165.us-east-2.compute.amazonaws.com " sudo docker image prune -f 
        cd funnel
        sudo docker-compose down
        git fetch origin
        git reset --hard origin/develop  &&  echo 'git fetched and hard reset'
        sudo docker-compose build && sudo docker-compose up -d
        "
echo 'Deployed to staging without db update successfully'