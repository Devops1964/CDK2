from aws_cdk import (
    core,
    aws_ecs as ecs,
    aws_ec2 as ec2
)

class CicdVpcEcsStack(core.Stack):
    def __init__(self, scope, id, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc_nonprod = ec2.Vpc(self, "cicd-vpc-nonprod", max_azs=2)
        vpc_prod = ec2.Vpc(self, "cicd-prod", max_azs=2)

        ecs.Cluster(self, "cicd-ecs-nonprod", capacity_providers=["FARGATE"],cluster_name="cicd-ecs-nonprod",vpc=vpc_nonprod)
        ecs.Cluster(self, "cicd-ecs-prod", capacity_providers=["FARGATE"],cluster_name="cicd-ecs-prod",vpc=vpc_prod)
      


