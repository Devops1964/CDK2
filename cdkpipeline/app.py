from aws_cdk import App, Environment
from cdkpipeline.cdkpipeline_stack import CdkpipelineStack

app = App()

# Retrieve context variables
aws_account = app.node.try_get_context("aws_account")
aws_region = app.node.try_get_context("aws_region")
microservice_name = app.node.try_get_context("microservice_name")

# Validate required context variables
if not aws_account or not aws_region or not microservice_name:
    raise ValueError("Missing required context values: aws_account, aws_region, or microservice_name")

# Define the deployment environment
env = Environment(account=aws_account, region=aws_region)

# Instantiate the pipeline stack
CdkpipelineStack(app, f"{microservice_name}-cicd-stack", env=env)

# Synthesize the app
app.synth()
