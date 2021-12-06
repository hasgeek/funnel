#!/bin/bash
set -e
echo 'Starting to Deploy...'
ssh ec2-user@3.144.184.165 "
          echo 'pruning unused docker images'
          docker image prune -f 
          #echo 'changing folder to funnel'
          cd funnel
          echo 'docker-compose down'
          docker-compose down
          echo 'fetching git repo'
          git fetch origin aws
          echo 'reset git repo'
          git reset --hard origin/aws  &&  echo 'git fetched and hard reset'
          echo 'fetching settings.py from s3'
          echo '${{ secrets.SERVER_ENV_DEV }}' > instance/settings.py
          ls instance
          cat instance/settings.py
          echo 'starting docker-compose'
          docker-compose up -f docker-compose.staging.yml -d
        "
echo 'Deployed to staging without db update successfully'