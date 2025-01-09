import boto3
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_vpc_id(stack_name, region_name="us-east-1", output_key="VpcId"):
    """Fetch the production VPC ID from the CloudFormation stack outputs."""
    client = boto3.client('cloudformation', region_name=region_name)

    try:
        response = client.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        outputs = stack.get('Outputs', [])

        # Extract the VPC ID
        vpc_id = next((o['OutputValue'] for o in outputs if o['OutputKey'] == output_key), None)

        if not vpc_id:
            logging.warning(f"Missing VPC ID in stack outputs for key: {output_key}.")
        else:
            logging.info(f"Retrieved VPC ID: {vpc_id}")

        return vpc_id

    except Exception as e:
        logging.error(f"Error retrieving VPC ID from stack {stack_name}: {e}")
        return None


def fetch_nacl_id(vpc_id, region_name="us-east-1"):
    """Fetch the Network ACL ID for the specified VPC ID."""
    ec2 = boto3.client('ec2', region_name=region_name)

    try:
        response = ec2.describe_network_acls()

        for nacl in response['NetworkAcls']:
            if nacl['VpcId'] == vpc_id:
                nacl_id = nacl['NetworkAclId']
                logging.info(f"Found NACL ID: {nacl_id} for VPC ID: {vpc_id}")
                return nacl_id

        logging.warning(f"No NACL found for VPC ID: {vpc_id}")
        return None

    except Exception as e:
        logging.error(f"Error fetching Network ACLs: {e}")
        return None


def fetch_ecs_sg_id(vpc_id, region_name="us-east-1"):
    """Fetch ECS Security Group ID for the specified VPC."""
    ec2 = boto3.client('ec2', region_name=region_name)
    try:
        response = ec2.describe_security_groups(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        for sg in response['SecurityGroups']:
            if 'ecs' in sg['GroupName'].lower():
                logging.info(f"Found ECS Security Group ID: {sg['GroupId']} for VPC ID: {vpc_id}")
                return sg['GroupId']
        logging.warning(f"No ECS Security Group found for VPC ID: {vpc_id}")
        return None
    except Exception as e:
        logging.error(f"Error fetching ECS Security Group: {e}")
        return None


def update_cdk_json(context_data, cdk_json_file, dry_run=False):
    """Update the cdk.json file with the VPC, NACL, and ECS SG mappings."""
    try:
        # Read existing cdk.json
        if os.path.exists(cdk_json_file):
            with open(cdk_json_file, 'r') as f:
                cdk_config = json.load(f)
        else:
            cdk_config = {"context": {}}

        # Update context with the new data
        cdk_config['context'].update(context_data)

        if dry_run:
            logging.info(f"Dry Run: Would update {cdk_json_file} with {context_data}")
        else:
            with open(cdk_json_file, 'w') as f:
                json.dump(cdk_config, f, indent=4)
            logging.info(f"Updated {cdk_json_file} with context: {context_data}")

    except Exception as e:
        logging.error(f"Error updating cdk.json: {e}")


if __name__ == "__main__":
    region_name = "eu-central-1"  # Replace with your desired AWS region
    stack_name = "ProductionVpcEcsStack"  # Updated stack name
    cdk_json_file = "cdk.json"
    dry_run = False  # Set to True for testing without modifying cdk.json

    # Step 1: Get the VPC ID from the CloudFormation stack
    vpc_prod_id = get_vpc_id(stack_name, region_name, output_key="VpcId")

    if not vpc_prod_id:
        logging.error("Unable to retrieve VPC ID. Please check your stack outputs.")
    else:
        # Step 2: Fetch the NACL ID for the production VPC
        nacl_prod_id = fetch_nacl_id(vpc_prod_id, region_name)

        # Step 2.1: Fetch ECS Security Group ID (optional)
        ecs_sg_id = fetch_ecs_sg_id(vpc_prod_id, region_name)

        # Step 3: Update cdk.json with all identifiers
        context_data = {
            "vpc_prod_id": vpc_prod_id,
            "nacl_prod_id": nacl_prod_id,
            "ecs_sg_id": ecs_sg_id
        }
        update_cdk_json(context_data, cdk_json_file, dry_run=dry_run)
