import boto3
import json
from datetime import datetime, timedelta

ssm = boto3.client('ssm', region_name='us-east-1')
rds_dr = boto3.client('rds', region_name='us-west-2')
ec2_dr = boto3.client('ec2', region_name='us-west-2')
sns_client = boto3.client('sns', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Clean up old test resources (RDS instances, EC2 instances, security groups)
    """
    
    sns_topic_arn = event.get('sns_topic_arn')
    max_age_hours = event.get('max_age_hours', 24)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'cleaned_resources': [],
        'errors': []
    }
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean up RDS test instances
        cleanup_rds_test_instances(cutoff_time, report)
        
        # Clean up EC2 test resources
        cleanup_ec2_test_resources(cutoff_time, report)
        
        # Send report if resources were cleaned
        if report['cleaned_resources'] and sns_topic_arn:
            send_cleanup_report(report, sns_topic_arn)
        
        print(json.dumps(report, indent=2, default=str))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report, default=str)
        }
        
    except Exception as e:
        error_message = f"Cleanup error: {str(e)}"
        print(error_message)
        report['errors'].append(error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps(report, default=str)
        }

def cleanup_rds_test_instances(cutoff_time, report):
    """Clean up old RDS test instances"""
    try:
        instances = rds_dr.describe_db_instances()
        
        for instance in instances['DBInstances']:
            instance_id = instance['DBInstanceIdentifier']
            
            if not instance_id.startswith('dr-test-'):
                continue
            
            creation_time = instance['InstanceCreateTime']
            if creation_time.replace(tzinfo=None) < cutoff_time:
                try:
                    rds_dr.delete_db_instance(
                        DBInstanceIdentifier=instance_id,
                        SkipFinalSnapshot=True,
                        DeleteAutomatedBackups=True
                    )
                    report['cleaned_resources'].append({
                        'type': 'rds_instance',
                        'id': instance_id
                    })
                except Exception as e:
                    report['errors'].append(f"Failed to delete RDS {instance_id}: {str(e)}")
    
    except Exception as e:
        report['errors'].append(f"Error cleaning RDS: {str(e)}")

def cleanup_ec2_test_resources(cutoff_time, report):
    """Clean up old EC2 test resources"""
    try:
        # Find test instances
        instances = ec2_dr.describe_instances(
            Filters=[
                {'Name': 'tag:Purpose', 'Values': ['RestoreTest']},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        )
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                launch_time = instance['LaunchTime']
                
                if launch_time.replace(tzinfo=None) < cutoff_time:
                    try:
                        # Terminate instance
                        ec2_dr.terminate_instances(InstanceIds=[instance_id])
                        report['cleaned_resources'].append({
                            'type': 'ec2_instance',
                            'id': instance_id
                        })
                    except Exception as e:
                        report['errors'].append(f"Failed to terminate {instance_id}: {str(e)}")
        
        # Clean up test security groups
        sgs = ec2_dr.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': ['dr-test-sg-*']}]
        )
        
        for sg in sgs['SecurityGroups']:
            try:
                ec2_dr.delete_security_group(GroupId=sg['GroupId'])
                report['cleaned_resources'].append({
                    'type': 'security_group',
                    'id': sg['GroupId']
                })
            except Exception as e:
                # SG might still be attached to instances
                pass
    
    except Exception as e:
        report['errors'].append(f"Error cleaning EC2: {str(e)}")

def send_cleanup_report(report, sns_topic_arn):
    """Send cleanup report"""
    message = f"""
🧹 Test Resource Cleanup Report

Timestamp: {report['timestamp']}
Cleaned Resources: {len(report['cleaned_resources'])}

{'='*50}
CLEANED RESOURCES:
{'='*50}

"""
    
    for resource in report['cleaned_resources']:
        message += f"- {resource['type'].upper()}: {resource['id']}\n"
    
    if report['errors']:
        message += f"""
{'='*50}
ERRORS:
{'='*50}

"""
        for error in report['errors']:
            message += f"- {error}\n"
    
    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject='🧹 DR Test Resource Cleanup Report',
            Message=message
        )
    except Exception as e:
        print(f"Error sending report: {str(e)}")
