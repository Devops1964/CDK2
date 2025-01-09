#!/usr/bin/env python3

from aws_cdk import App, Environment
from cicdvpcecs.cicdvpcecs_stack import CicdVpcEcsStack

app = App()

# Retrieve context values for AWS account and region
aws_account = app.node.try_get_context("aws_account")
aws_region = app.node.try_get_context("aws_region")

# Define the environment for the stack
env = Environment(account=aws_account, region=aws_region)

# Initialize the stack
CicdVpcEcsStack(app, "cicd-vpc-ecs", env=env)

# Synthesize the app
app.synth()
