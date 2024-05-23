from aws_cdk import (
    core,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_ec2 as ec2
)


class CdkpipelineStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

       
        # Get the microservice name from context
        microservice_name = self.node.try_get_context("microservice_name")
        
        # Get the code commit parameters from context
        repository_name = microservice_name
        repository_constr_id = microservice_name + "-codecommit-id"
        branch_name = self.node.try_get_context("code_commit_branch_name")
        repository_description = "Repository for " + microservice_name
        s3_bucket_for_code = self.node.try_get_context("code_commit_s3_bucket_for_code")
        s3_object_key_for_code = self.node.try_get_context("code_commit_s3_object_key_for_code")

        # Get ecr parameters from context
        ecr_repo_constr_id = microservice_name + "-ecrrepo-id"
        ecr_repo_name = microservice_name

        # Get code build parameters from context
        code_build_constr_id = microservice_name + "-codebuild-id"
        code_build_project_name = microservice_name

        # Get ecs fargate service parameters from context
        ecs_service_name = microservice_name
        ecs_service_role_contr_id = microservice_name + "ecsrole-id"
        ecs_service_role_name = microservice_name + "-ecs-taskexecution-role"
        ecs_fargate_constr_id = microservice_name + "-ecs-fargate-id"
        ecs_fargate_constr_id_prod = microservice_name + "-prod-ecs-fargate-id"
        
        # Get code pipeline parameters from context
        pipeline_constr_id = microservice_name + "-codepipeline-id"
        pipeline_name = microservice_name
       
        # Create the repository and add the starter code. The starter code is available in the S3 bucket defined in cdk.json

        cfn_resource = codecommit.CfnRepository(self,repository_constr_id,repository_name=repository_name)
        cfn_resource.add_property_override("Code.BranchName",branch_name)
        cfn_resource.add_property_override("Code.S3.Bucket",s3_bucket_for_code)
        cfn_resource.add_property_override("Code.S3.Key",s3_object_key_for_code)
        cfn_resource.add_property_override("RepositoryDescription",repository_description)

        # Get handle to code commit repository object to use in code pipeline source action
        codecommit_repo = codecommit.Repository.from_repository_name(self,"Repository",repository_name = repository_name)

        # Get handle to the ecr repository to use by code build
        ecr_repo = ecr.Repository(self, ecr_repo_constr_id, repository_name = ecr_repo_name)

        # Create the starter ECS Fargate Service using AWS provided public nginx image. This will be updated later with the built image
        # by the pipeline
        starter_image = ecs.ContainerImage.from_registry("public.ecr.aws/nginx/nginx:1.25-bookworm")
        execution_policy = iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name = "service-role/AmazonECSTaskExecutionRolePolicy")
        execution_role = iam.Role(self,ecs_service_role_contr_id,assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),managed_policies=[execution_policy],role_name=ecs_service_role_name)

        vpc_nonprod_id = self.node.try_get_context("vpc_nonprod_id")
        vpc_prod_id = self.node.try_get_context("vpc_prod_id")
        ecssg_nonprod_id = self.node.try_get_context("ecssg_nonprod_id")
        ecssg_prod_id = self.node.try_get_context("ecssg_prod_id")
        ecs_nonprod_name = self.node.try_get_context("ecs_nonprod_name")
        ecs_prod_name = self.node.try_get_context("ecs_prod_name")

        vpc_nonprod = ec2.Vpc.from_lookup(self, "vpc-nonprod",vpc_id=vpc_nonprod_id)
        vpc_prod = ec2.Vpc.from_lookup(self, "vpc-prod",vpc_id=vpc_prod_id)

        ecssg_nonprod = ec2.SecurityGroup.from_security_group_id(self, "ecssg-nonprod",security_group_id = ecssg_nonprod_id)
        ecssg_prod = ec2.SecurityGroup.from_security_group_id(self, "ecssg-prod",security_group_id = ecssg_prod_id)

        ecs_nonprod = ecs.Cluster.from_cluster_attributes(self,"ecs-nonprod",cluster_name=ecs_nonprod_name,vpc=vpc_nonprod,security_groups=[ecssg_nonprod])
        ecs_prod = ecs.Cluster.from_cluster_attributes(self,"ecs-prod",cluster_name=ecs_prod_name,vpc=vpc_prod,security_groups=[ecssg_prod])

        alb_fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, ecs_fargate_constr_id,
            #task_definition=alb_task_definition,
            task_image_options= {
                "image": starter_image,
                "container_name": "app",
                "execution_role": execution_role
            },
            #assign_public_ip=True,
            desired_count = 2,
            service_name = ecs_service_name,
            listener_port = 80,
            cluster=ecs_nonprod
        )
        fargateservice = alb_fargate_service.service


        alb_fargate_service_prod = ecs_patterns.ApplicationLoadBalancedFargateService(self, ecs_fargate_constr_id_prod,
            #task_definition=alb_task_definition,
            task_image_options= {
                "image": starter_image,
                "container_name": "app",
                "execution_role": execution_role
            },
            #assign_public_ip=True,
            desired_count = 2,
            service_name = ecs_service_name,
            listener_port = 80,
            cluster=ecs_prod
        )
        fargateservice_prod = alb_fargate_service_prod.service


        # Create the CodeBuild project that creates the Docker image, and pushes it to the ecr repository
        codebuild_project = codebuild.PipelineProject(self, code_build_constr_id,project_name=code_build_project_name,
            environment=codebuild.BuildEnvironment(
                # Required to run Docker
                privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": [
                            "$(aws ecr get-login --region $AWS_DEFAULT_REGION --no-include-email)",
                            "echo $REPOSITORY_URI",
                            "docker build -t $REPOSITORY_URI:latest .",
                            "docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "docker push $REPOSITORY_URI:latest",
                            "docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "export imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "printf '[{\"name\":\"app\",\"imageUri\":\"%s\"}]' $REPOSITORY_URI:$imageTag > imagedefinitions.json"
                        ]
                    }
                },
                "env": {
                    # save the imageTag environment variable as a CodePipeline Variable
                     "exported-variables": ["imageTag"]
                },
                "artifacts": {
                    "files": "imagedefinitions.json",
                    "secondary-artifacts": {
                        "imagedefinitions": {
                            "files": "imagedefinitions.json",
                            "name": "imagedefinitions"
                        }
                    }
                }
            }),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=ecr_repo.repository_uri
                )
            }
        )
        # Grant push pull permissions on ecr repo to code build project needed for `docker push`
        ecr_repo.grant_pull_push(codebuild_project)

        # Define the source action for code pipeline
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit",
            repository=codecommit_repo,
            output=source_output,
            code_build_clone_output=True
            )
        # Define the build action for code pipeline
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuild",
            project=codebuild_project,
            input=source_output,
            outputs=[codepipeline.Artifact("imagedefinitions")],
            execute_batch_build=False
        )

        # Define the deploy action for code pipeline
        deploy_action = codepipeline_actions.EcsDeployAction(
            action_name="DeployECS",
            service=fargateservice,
            input=codepipeline.Artifact("imagedefinitions")
        )

        manual_approval_prod = codepipeline_actions.ManualApprovalAction(
            action_name="Approve-Prod-Deploy",
            run_order=1
        )

        deploy_action_prod = codepipeline_actions.EcsDeployAction(
            action_name="DeployECS",
            service=fargateservice_prod,
            input=codepipeline.Artifact("imagedefinitions"),
            run_order=2
        )

        # Create the pipeline
        codepipeline.Pipeline(self, pipeline_constr_id, pipeline_name = pipeline_name,
            stages=[{
                "stageName": "Source",
                "actions": [source_action]
            }, {
                "stageName": "Build",
                "actions": [build_action]
            }, {
                "stageName": "Deploy-NonProd",
                "actions": [deploy_action]
            }, {
                "stageName": "Deploy-Prod",
                "actions": [
                    manual_approval_prod,
                    deploy_action_prod
                ]
            }
            ]
        )

                    
