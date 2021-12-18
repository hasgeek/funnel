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
s3bucket="$(date +'%Y-%m')/$(date +'%Y-%m-%d')/"
echo $s3bucket
latestfile=$(aws s3api --profile production list-objects-v2 --bucket hasgeek-instant-db-backup --prefix ${s3bucket} --query 'sort_by(Contents, &LastModified)[-1].Key' --output text)
echo $latestfile
LOCAL_DUMP_PATH="./instantbackups.gz"
aws s3 --profile production cp s3://hasgeek-instant-db-backup/${latestfile} $LOCAL_DUMP_PATH
gunzip instantbackups.gz
docker exec -i "${DOCKER_DB_NAME}" pg_restore -C --clean --no-acl --no-owner  < instantbackups
docker-compose stop postgres --remove-orphans
docker-compose -f docker-compose.staging.yml up -d
