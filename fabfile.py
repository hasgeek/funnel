import os
from fabric import Connection
#from fabric.api import env, run
#from fabric.context_managers import cd
import boto3
from fabric import task

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

profile_name = 'default'


def set_hosts(environment):
    print(environment)
    hosts = ''
    user = 'ec2-user'
    profile_name = 'default'
    tag = 'v2beta'
    key = 'tag:' + tag
    home = os.path.expanduser('~')
    print(home)
    if environment == 'production':
        profile_name = 'production'
        tag = 'v2beta'
        key = 'tag:' + tag
        hosts = _get_public_dns(production_region, key, profile_name, '*')
        user = 'ec2-user'
    if environment == 'cron':
        profile_name = 'production'
        tag = 'v2beta-cron'
        key = 'tag:' + tag
        hosts = _get_public_dns(production_region, key, profile_name, '*')
        user = "ec2-user"
    elif environment == 'vps':
        print('setting vps environment')
        hosts = 'e2e.hasgeek.com'
        user = 'hasgeek'
    elif environment == 'staging':
        tag = 'v2-alpha-autodeploy'
        key = 'tag:' + tag
        hosts = _get_public_dns(staging_region, key, profile_name, '*')
        user = 'ec2-user'
    else:
        pass
        # print('invalid environment')
    return hosts, user

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

@task
def staging(arg):
    # This is staging only and is run with the following command:
    # fab staging
    hosts, user = set_hosts('staging')
    for host in hosts:
        with Connection(host=host, user=user) as c:  
            with c.cd('funnel'):
                c.run('sh staging_deploy.sh')
                c.run('docker-compose -f docker-compose.staging.yml up -d')

@task
def instantbackup(arg):
    # This is vps only and is run with the following command:
    # fab backup
    hosts, user = set_hosts('vps')
    with Connection(host=hosts, user=user) as c:  
        c.run('sh instant-backup-s3-sql.sh')
    hosts, user = set_hosts('staging')
    with Connection(host=hosts[0], user=user) as c:  
        c.run('cd funnel')
        c.run('sh staging-restore-db-from-s3.sh')

@task
def periodic(arg, command):
    hosts, user = set_hosts('production')
    for host in hosts:
        with Connection(host=host, user=user) as c:  
            with c.cd('funnel'):
                flask_periodic_com = 'docker-compose run web flask periodic %s' % command
                c.run(flask_periodic_com)
