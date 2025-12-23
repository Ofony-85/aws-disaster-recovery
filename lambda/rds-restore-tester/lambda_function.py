import boto3
import json
from datetime import datetime
import time

rds_primary = boto3.client('rds', region_name='us-east-1')
rds_dr = boto3.client('rds', region_name='us-west-2')
sns_client = boto3.client('sns', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Test RDS restore capability by restoring latest snapshot to a test instance
    """
    
    config = event.get('config', {})
    source_db_id = config.get('source_db_id', 'dr-project-primary-db')
    test_region = config.get('test_region', 'us-west-2')
    sns_topic_arn = config.get('sns_topic_arn')
    
    test_id = f"restore-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    report = {
        'test_id': test_id,
        'timestamp': datetime.now().isoformat(),
        'status': 'in_progress',
        'steps': []
    }
    
    try:
        # Step 1: Get latest snapshot from DR region
        report['steps'].append({
            'step': 'get_snapshot',
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        })
        
        dr_client = rds_dr if test_region == 'us-west-2' else rds_primary
        
        snapshots = dr_client.describe_db_snapshots(
            SnapshotType='automated'
        )
        
        if not snapshots['DBSnapshots']:
            raise Exception("No snapshots found for testing")
        
        # Get most recent available snapshot
        available_snapshots = [s for s in snapshots['DBSnapshots'] 
                             if s['Status'] == 'available']
        
        if not available_snapshots:
            raise Exception("No available snapshots found")
        
        latest_snapshot = max(available_snapshots, 
                            key=lambda x: x['SnapshotCreateTime'])
        
        snapshot_id = latest_snapshot['DBSnapshotIdentifier']
        
        report['steps'][-1]['status'] = 'completed'
        report['steps'][-1]['snapshot_id'] = snapshot_id
        report['snapshot_id'] = snapshot_id
        
        # Step 2: Restore to test instance
        report['steps'].append({
            'step': 'restore_instance',
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        })
        
        test_instance_id = f"dr-test-{test_id}"
        
        # Get VPC security group for the region
        if test_region == 'us-west-2':
            # Use default security group for testing
            vpcs = boto3.client('ec2', region_name='us-west-2').describe_vpcs(
                Filters=[{'Name': 'isDefault', 'Values': ['true']}]
            )
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            
            sgs = boto3.client('ec2', region_name='us-west-2').describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'group-name', 'Values': ['default']}
                ]
            )
            sg_id = sgs['SecurityGroups'][0]['GroupId']
        else:
            # Get security group from source instance
            source_db = rds_primary.describe_db_instances(
                DBInstanceIdentifier=source_db_id
            )
            sg_id = source_db['DBInstances'][0]['VpcSecurityGroups'][0]['VpcSecurityGroupId']
        
        # Restore snapshot
        restore_response = dr_client.restore_db_instance_from_db_snapshot(
            DBInstanceIdentifier=test_instance_id,
            DBSnapshotIdentifier=snapshot_id,
            DBInstanceClass='db.t3.micro',
            VpcSecurityGroupIds=[sg_id],
            PubliclyAccessible=False,
            Tags=[
                {'Key': 'Purpose', 'Value': 'RestoreTest'},
                {'Key': 'TestID', 'Value': test_id},
                {'Key': 'AutoDelete', 'Value': 'true'}
            ]
        )
        
        report['steps'][-1]['status'] = 'completed'
        report['steps'][-1]['instance_id'] = test_instance_id
        report['test_instance_id'] = test_instance_id
        
        # Step 3: Wait for instance to be available (async - will be handled separately)
        report['steps'].append({
            'step': 'wait_for_available',
            'status': 'pending',
            'timestamp': datetime.now().isoformat(),
            'message': 'Instance restore initiated. Will verify availability separately.'
        })
        
        report['status'] = 'restore_initiated'
        report['message'] = f"Restore test initiated. Instance {test_instance_id} is being created."
        
        # Send notification
        if sns_topic_arn:
            send_notification(report, sns_topic_arn, 'initiated')
        
        # Store test instance ID for cleanup
        store_test_instance(test_instance_id, test_region)
        
        print(json.dumps(report, indent=2, default=str))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report, default=str)
        }
        
    except Exception as e:
        error_message = f"RDS restore test failed: {str(e)}"
        print(error_message)
        
        report['status'] = 'failed'
        report['error'] = str(e)
        
        if sns_topic_arn:
            send_notification(report, sns_topic_arn, 'failed')
        
        return {
            'statusCode': 500,
            'body': json.dumps(report, default=str)
        }

def store_test_instance(instance_id, region):
    """Store test instance info in parameter store for cleanup"""
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        ssm.put_parameter(
            Name=f'/dr/test-instances/{instance_id}',
            Value=json.dumps({
                'instance_id': instance_id,
                'region': region,
                'created': datetime.now().isoformat()
            }),
            Type='String',
            Overwrite=True,
            Tags=[
                {'Key': 'Purpose', 'Value': 'RestoreTest'},
                {'Key': 'AutoCleanup', 'Value': 'true'}
            ]
        )
    except Exception as e:
        print(f"Error storing test instance info: {str(e)}")

def send_notification(report, sns_topic_arn, status_type):
    """Send SNS notification"""
    
    if status_type == 'initiated':
        subject = "✅ RDS Restore Test Initiated"
        message = f"""
RDS Restore Test Started

Test ID: {report['test_id']}
Timestamp: {report['timestamp']}

Snapshot Used: {report.get('snapshot_id', 'N/A')}
Test Instance: {report.get('test_instance_id', 'N/A')}

Status: Restore in progress
Expected completion: 10-15 minutes

The instance will be automatically validated and cleaned up.
        """
    elif status_type == 'failed':
        subject = "❌ RDS Restore Test Failed"
        message = f"""
RDS Restore Test Failed

Test ID: {report['test_id']}
Timestamp: {report['timestamp']}

Error: {report.get('error', 'Unknown error')}

Please investigate the issue.
        """
    else:
        subject = "📋 RDS Restore Test Status"
        message = json.dumps(report, indent=2, default=str)
    
    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject=subject,
            Message=message
        )
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
