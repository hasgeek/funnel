from fabric.api import env, run
from fabric.context_managers import cd
import boto3

staging_region = 'us-east-2'
production_region = 'ap-south-1'

# AWS Credentials should be stored in ~/.aws/credentials
# of the form below. Default will be applied for the staging
# server and production will be applied for the production
# and cron servers
#
# [default]
# aws_access_key_id=foo
# aws_secret_access_key=bar
#
# [production]
# aws_access_key_id=foo3
# aws_secret_access_key=bar3
#


env.key_filename = [
    "~/.ssh/id_rsa",  # vps
    "~/.ssh/v2betaone.pem",  # production
    "~/.ssh/v2-alpha.pem",  # staging
]


def set_hosts(environment):
    profile_name = 'default'
    if environment == 'production':
        profile_name = 'production'
        tag = 'v2beta'
        key = "tag:" + tag
        env.hosts = _get_public_dns(production_region, key, profile_name, '*')
        env.user = "ec2-user"
    if environment == 'cron':
        profile_name = 'production'
        tag = 'v2beta-cron'
        key = "tag:" + tag
        env.hosts = _get_public_dns(production_region, key, profile_name, '*')
        env.user = "ec2-user"
    elif environment == 'vps':
        env.hosts = ''
        env.user = "hasgeek"
    elif environment == 'staging':
        tag = 'v2-alpha-autodeploy'
        key = "tag:" + tag
        env.hosts = _get_public_dns(staging_region, key, profile_name, '*')
        env.user = "ec2-user"
    else:
        pass
        # print('invalid environment')


def _get_public_dns(region, key, profile_name, value="*"):
    public_dns = []
    boto3.setup_default_session(profile_name=profile_name)
    client = boto3.client('ec2', region_name=region)
    reservations = client.describe_instances(Filters=[{'Name': key, 'Values': ['*']}])
    # print(reservations)
    for reservation in reservations['Reservations']:
        for instance in reservation['Instances']:
            # print(instance)
            # print("Instance", instance['PublicDnsName'])
            public_dns.append(str(instance['PublicDnsName']))
    return public_dns


# This is staging specific and is run with the following command:
# fab set_hosts:staging deploy_to_staging
def deploy_to_staging():
    with cd('funnel'):
        run('sh staging_deploy.sh')
        run('docker-compose -f docker-compose.staging.yml up -d')

def flask(command):
    run('flask')
