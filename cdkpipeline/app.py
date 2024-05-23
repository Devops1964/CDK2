#!/usr/bin/env python3

from aws_cdk import core

from cdkpipeline.cdkpipeline_stack import CdkpipelineStack

app = core.App()

aws_account = app.node.try_get_context("aws_account")
aws_region = app.node.try_get_context("aws_region")
microservice_name = app.node.try_get_context("microservice_name")

env = core.Environment(account=aws_account, region=aws_region)

app_stack_name = microservice_name + "-cicd-stack"
CdkpipelineStack(app, app_stack_name , env=env)
app.synth()

