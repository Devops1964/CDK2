from aws_cdk import (
    App,
    Stack,
    Environment,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class CdkpipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Retrieve context variables
        microservice_name = self.node.try_get_context("microservice_name")
        github_context = self.node.try_get_context("github")
        if not github_context:
            raise ValueError("Missing GitHub context configuration in cdk.json")

        github_owner = github_context.get("owner")
        github_repo = github_context.get("repo")
        github_branch = github_context.get("branch")
        github_token_secret_name = github_context.get("token_secret")

        # Validate GitHub context variables
        if not all([github_owner, github_repo, github_branch, github_token_secret_name]):
            raise ValueError("Missing required GitHub context values.")

        # Retrieve GitHub token from Secrets Manager
        github_token = secretsmanager.Secret.from_secret_name_v2(
            self, "GitHubTokenSecret", github_token_secret_name
        ).secret_value

        # Create ECR repository
        ecr_repo = ecr.Repository(
            self, f"{microservice_name}-ecrrepo-id", repository_name=microservice_name
        )

        # ECS task execution role
        execution_role = iam.Role(
            self,
            f"{microservice_name}-ecsrole-id",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

        # Create CodeBuild project
        codebuild_project = codebuild.PipelineProject(
            self,
            f"{microservice_name}-codebuild-id",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,  # Supports Docker
                privileged=True,  # Required for Docker builds
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=ecr_repo.repository_uri
                )
            },
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": [
                            "echo Installing dependencies...",
                            "apt-get update && apt-get install -y jq"
                        ]
                    },
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            "$(aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin 529088253053.dkr.ecr.eu-central-1.amazonaws.com/my-microservice)",
                            "COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)",
                            "IMAGE_TAG=${COMMIT_HASH:=latest}",
                            "echo Commit hash is $COMMIT_HASH",
                            "echo Tagging image with $IMAGE_TAG",
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "docker build -t $REPOSITORY_URI:latest .",
                            "docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG",
                            "echo Running unit tests...",
                            "./run-tests.sh",
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Pushing Docker images...",
                            "docker push $REPOSITORY_URI:latest",
                            "docker push $REPOSITORY_URI:$IMAGE_TAG",
                            "echo Generating imagedefinitions.json...",
                            "printf '[{\"name\":\"app\",\"imageUri\":\"%s\"}]' $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json",
                            "echo Cleaning up...",
                            "docker rmi $REPOSITORY_URI:latest",
                            "docker rmi $REPOSITORY_URI:$IMAGE_TAG",
                        ]
                    }
                },
                "artifacts": {
                    "files": ["imagedefinitions.json"]
                }
            }),
        )
        ecr_repo.grant_pull_push(codebuild_project)

        # Define GitHub source action
        source_output = codepipeline.Artifact()
        github_source_action = codepipeline_actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner=github_owner,
            repo=github_repo,
            branch=github_branch,
            oauth_token=github_token,
            output=source_output,
        )

        # Define the build action
        build_output = codepipeline.Artifact("BuildOutput")
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuild",
            project=codebuild_project,
            input=source_output,
            outputs=[build_output],
        )

        # Create Fargate service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f"{microservice_name}-ecs-fargate-id",
            task_image_options={
                "image": ecs.ContainerImage.from_registry("public.ecr.aws/nginx/nginx:1.25-bookworm"),
                "container_name": "app",
                "execution_role": execution_role,
            },
            desired_count=2,
            service_name=microservice_name,
        )

        # Define ECS Deploy Action
        deploy_action = codepipeline_actions.EcsDeployAction(
            action_name="ECS_Deploy",
            service=fargate_service.service,
            input=build_output,
        )

        # Create the pipeline
        codepipeline.Pipeline(
            self,
            f"{microservice_name}-pipeline-id",
            pipeline_name=f"{microservice_name}-pipeline",
            stages=[
                {
                    "stageName": "Source",
                    "actions": [github_source_action],
                },
                {
                    "stageName": "Build",
                    "actions": [build_action],
                },
                {
                    "stageName": "Deploy",
                    "actions": [deploy_action],
                },
            ],
        )


# Initialize the CDK app and stack
app = App()

# Retrieve AWS account and region from context
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
