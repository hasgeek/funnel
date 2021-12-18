#!/bin/bash
set -e
#!/bin/bash
set -e
echo "pruning unused docker images"
docker image prune -f
echo "docker-compose down"
docker-compose down --remove-orphans
echo "git repo pull"
git pull
#echo "reset git repo"
#git reset --hard origin/aws && echo "git fetched and hard reset"
echo "fetching settings.py"
aws s3 cp s3://v2-alpha-test-environment-files/container_env instance/settings.py
ls instance
#echo "starting docker-compose"
aws s3 cp s3://v2-alpha-test-environment-files/container_env instance/settings.py
echo "starting the db"
docker-compose -f docker-compose.staging.yml up -d postgres
DOCKER_DB_NAME="$(docker-compose -f docker-compose.staging.yml ps -q postgres)"
echo $DOCKER_DB_NAME 
# get the latest backup from s3 and save it to instantbackups
s3bucket = "s3://hasgeek-instant-db-backup/$(date +'%Y-%m')/instant-$(date +'%Y-%m-%d')"
latestfile = $(aws s3api list-objects --bucket ${s3bucket} --query 'sort_by(Contents, &LastModified)[-1].Key' --output text)
echo $latestfile
LOCAL_DUMP_PATH = "/tmp/instantbackups"
aws s3 cp ${s3bucket}${latestfile} $LOCAL_DUMP_PATH
docker exec -i "${DOCKER_DB_NAME}" pg_restore -C --clean --no-acl --no-owner  < "${LOCAL_DUMP_PATH}"
docker-compose stop postgres --remove-orphans
docker-compose -f docker-compose.staging.yml up -d