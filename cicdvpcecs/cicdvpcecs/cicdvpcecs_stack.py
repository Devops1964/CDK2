from aws_cdk import (
    Stack,
    CfnOutput
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from constructs import Construct

class CicdVpcEcsStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # VPC for Non-Production with Single NAT Gateway
        vpc_nonprod = ec2.Vpc(self, "CicdVpcNonProd",
            max_azs=2,
            ip_addresses=ec2.IpAddresses.cidr("10.1.0.0/16"),
            nat_gateways=1,  # Reduce NAT Gateways to save EIP usage
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # VPC for Production with Single NAT Gateway
        vpc_prod = ec2.Vpc(self, "CicdVpcProd",
            max_azs=2,
            ip_addresses=ec2.IpAddresses.cidr("10.2.0.0/16"),
            nat_gateways=1,  # Reduce NAT Gateways to save EIP usage
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Security Groups
        ecssg_nonprod = ec2.SecurityGroup(self, "EcsSgNonProd", vpc=vpc_nonprod)
        ecssg_prod = ec2.SecurityGroup(self, "EcsSgProd", vpc=vpc_prod)

        # ECS Clusters
        ecs_nonprod = ecs.Cluster(self, "CicdEcsNonProd", cluster_name="cicd-ecs-nonprod", vpc=vpc_nonprod)
        ecs_prod = ecs.Cluster(self, "CicdEcsProd", cluster_name="cicd-ecs-prod", vpc=vpc_prod)

        # Outputs
        CfnOutput(self, "VpcNonProdId", value=vpc_nonprod.vpc_id, description="VPC ID for Non-Production")
        CfnOutput(self, "VpcProdId", value=vpc_prod.vpc_id, description="VPC ID for Production")
        CfnOutput(self, "EcsSgNonProdId", value=ecssg_nonprod.security_group_id, description="Non-Prod ECS SG ID")
        CfnOutput(self, "EcsSgProdId", value=ecssg_prod.security_group_id, description="Prod ECS SG ID")
        CfnOutput(self, "EcsNonProdName", value=ecs_nonprod.cluster_name, description="Non-Prod ECS Cluster Name")
        CfnOutput(self, "EcsProdName", value=ecs_prod.cluster_name, description="Prod ECS Cluster Name")

        # Outputs for Public Subnets
        CfnOutput(self, "VpcNonProdPublicSubnets",
            value=", ".join([subnet.subnet_id for subnet in vpc_nonprod.public_subnets]),
            description="Public Subnet IDs for Non-Production VPC"
        )
        CfnOutput(self, "VpcProdPublicSubnets",
            value=", ".join([subnet.subnet_id for subnet in vpc_prod.public_subnets]),
            description="Public Subnet IDs for Production VPC"
        )
