#!/bin/bash
echo 'Starting to Deploy...'
ssh -o StrictHostKeyChecking=no ec2-user@ec2-3-144-184-165.us-east-2.compute.amazonaws.com "ls"
echo 'Deployed to staging without db update successfully'