echo "pruning unused docker images"
docker image prune -f
echo "changing folder to funnel"
cd funnel
echo "docker-compose down"
docker-compose down
echo "fetching git repo"
git pull
#echo "reset git repo"
#git reset --hard origin/aws && echo "git fetched and hard reset"
echo "fetching settings.py"
aws s3 cp s3://v2-alpha-test-environment-files/container_env instance/settings.py
ls instance
cat instance/settings.py
echo "starting docker-compose"
docker-compose -f docker-compose.staging.yml up -d
echo "Deployed to staging without db update successfully"
