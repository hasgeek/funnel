from boto.ec2 import connect_to_region
from fabric.api import env, run

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


env.key_filename = ["~/.ssh/id_rsa", "~/.ssh/v2betaone.pem", "~/.ssh/v2-alpha.pem"]


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
        tag = 'v2alpha'
        key = "tag:" + tag
        env.hosts = _get_public_dns(staging_region, key, profile_name, '*')
        env.user = "ec2-user"
    else:
        print('invalid environment')


def _get_public_dns(region, key, profile_name, value="*"):
    public_dns = []
    connection = _create_connection(region, profile_name)
    reservations = connection.get_all_instances(filters={key: value})
    for reservation in reservations:
        for instance in reservation.instances:
            print("Instance", instance.public_dns_name)
            public_dns.append(str(instance.public_dns_name))
    return public_dns


def _create_connection(region, profile_name):
    print("Connecting to ", region)

    conn = connect_to_region(
        region_name=region,
        profile_name=profile_name,
    )

    print("Connection with AWS established")
    return connection


def deploy_to_staging():
    run('sh ./staging_deploy.sh')
