#!/usr/bin/env python3

from aws_cdk import core

from cicdvpcecs.cicdvpcecs_stack import CicdVpcEcsStack

app = core.App()

aws_account = app.node.try_get_context("aws_account")
aws_region = app.node.try_get_context("aws_region")

env = core.Environment(account=aws_account, region=aws_region)

CicdVpcEcsStack(app,"cicd-vpc-ecs", env=env)

app.synth()
