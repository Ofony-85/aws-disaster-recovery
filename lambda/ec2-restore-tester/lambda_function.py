import boto3
import json
from datetime import datetime

ec2_dr = boto3.client('ec2', region_name='us-west-2')
sns_client = boto3.client('sns', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Test EC2 restore by launching instance from AMI in DR region
    """
    
    config = event.get('config', {})
    sns_topic_arn = config.get('sns_topic_arn')
    
    test_id = f"ec2-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    report = {
        'test_id': test_id,
        'timestamp': datetime.now().isoformat(),
        'status': 'in_progress'
    }
    
    try:
        # Get latest AMI in DR region
        amis = ec2_dr.describe_images(
            Owners=['self'],
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        
        if not amis['Images']:
            raise Exception("No AMIs found in DR region")
        
        latest_ami = max(amis['Images'], key=lambda x: x['CreationDate'])
        ami_id = latest_ami['ImageId']
        
        report['ami_id'] = ami_id
        report['ami_name'] = latest_ami['Name']
        
        # Get default VPC and subnet
        vpcs = ec2_dr.describe_vpcs(
            Filters=[{'Name': 'isDefault', 'Values': ['true']}]
        )
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        
        subnets = ec2_dr.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        subnet_id = subnets['Subnets'][0]['SubnetId']
        
        # Create security group for test
        sg_name = f'dr-test-sg-{test_id}'
        sg = ec2_dr.create_security_group(
            GroupName=sg_name,
            Description='Security group for DR restore test',
            VpcId=vpc_id
        )
        sg_id = sg['GroupId']
        
        # Add SSH rule
        ec2_dr.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )
        
        # Launch test instance
        instance = ec2_dr.run_instances(
            ImageId=ami_id,
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[sg_id],
            SubnetId=subnet_id,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': f'dr-test-{test_id}'},
                    {'Key': 'Purpose', 'Value': 'RestoreTest'},
                    {'Key': 'TestID', 'Value': test_id},
                    {'Key': 'AutoDelete', 'Value': 'true'}
                ]
            }]
        )
        
        instance_id = instance['Instances'][0]['InstanceId']
        
        report['instance_id'] = instance_id
        report['security_group_id'] = sg_id
        report['status'] = 'instance_launched'
        
        # Store for cleanup
        store_test_resources(test_id, instance_id, sg_id)
        
        # Send notification
        if sns_topic_arn:
            send_notification(report, sns_topic_arn)
        
        print(json.dumps(report, indent=2, default=str))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report, default=str)
        }
        
    except Exception as e:
        error_message = f"EC2 restore test failed: {str(e)}"
        print(error_message)
        
        report['status'] = 'failed'
        report['error'] = str(e)
        
        if sns_topic_arn:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject='❌ EC2 Restore Test Failed',
                Message=error_message
            )
        
        return {
            'statusCode': 500,
            'body': json.dumps(report, default=str)
        }

def store_test_resources(test_id, instance_id, sg_id):
    """Store test resource info for cleanup"""
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        ssm.put_parameter(
            Name=f'/dr/test-resources/{test_id}',
            Value=json.dumps({
                'test_id': test_id,
                'instance_id': instance_id,
                'security_group_id': sg_id,
                'region': 'us-west-2',
                'created': datetime.now().isoformat()
            }),
            Type='String',
            Overwrite=True
        )
    except Exception as e:
        print(f"Error storing test resources: {str(e)}")

def send_notification(report, sns_topic_arn):
    """Send notification"""
    message = f"""
✅ EC2 Restore Test Initiated

Test ID: {report['test_id']}
Timestamp: {report['timestamp']}

AMI Used: {report['ami_id']} ({report['ami_name']})
Test Instance: {report['instance_id']}
Security Group: {report['security_group_id']}

Status: Instance launched successfully
Region: us-west-2

The instance will be validated and cleaned up automatically.
    """
    
    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject='✅ EC2 Restore Test Started',
            Message=message
        )
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
