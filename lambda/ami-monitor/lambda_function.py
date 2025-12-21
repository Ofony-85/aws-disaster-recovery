import boto3
import json
from datetime import datetime, timedelta

ec2_primary = boto3.client('ec2', region_name='us-east-1')
ec2_dr = boto3.client('ec2', region_name='us-west-2')
sns_client = boto3.client('sns')

def lambda_handler(event, context):
    """
    Monitor AMI backups and send alerts if backups are missing
    """
    
    instance_id = event['instance_id']
    sns_topic_arn = event['sns_topic_arn']
    max_age_hours = event.get('max_age_hours', 48)
    
    issues = []
    report = {
        'timestamp': datetime.now().isoformat(),
        'instance_id': instance_id
    }
    
    try:
        # Check AMIs in primary region
        primary_amis = ec2_primary.describe_images(
            Filters=[
                {'Name': 'tag:Backup', 'Values': ['daily']},
                {'Name': 'state', 'Values': ['available']}
            ],
            Owners=['self']
        )
        
        report['primary_ami_count'] = len(primary_amis['Images'])
        
        # Check AMIs in DR region
        dr_amis = ec2_dr.describe_images(
            Filters=[
                {'Name': 'state', 'Values': ['available']}
            ],
            Owners=['self']
        )
        
        report['dr_ami_count'] = len(dr_amis['Images'])
        
        # Check for recent backups
        if primary_amis['Images']:
            latest_ami = max(primary_amis['Images'], 
                           key=lambda x: x['CreationDate'])
            
            creation_time = datetime.strptime(
                latest_ami['CreationDate'], 
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            
            age_hours = (datetime.utcnow() - creation_time).total_seconds() / 3600
            report['latest_ami_age_hours'] = round(age_hours, 2)
            
            if age_hours > max_age_hours:
                issues.append(
                    f"⚠️ Latest AMI is {round(age_hours, 1)} hours old (threshold: {max_age_hours}h)"
                )
        else:
            issues.append("❌ No AMIs found in primary region")
        
        # Check DR region
        if not dr_amis['Images']:
            issues.append("⚠️ No AMIs found in DR region")
        
        # Check DLM policy status
        dlm_policies = boto3.client('dlm', region_name='us-east-1').get_lifecycle_policies()
        
        enabled_policies = [p for p in dlm_policies['Policies'] if p['State'] == 'ENABLED']
        report['dlm_policies_enabled'] = len(enabled_policies)
        
        if not enabled_policies:
            issues.append("❌ No enabled DLM policies found")
        
        report['issues'] = issues
        report['status'] = 'healthy' if not issues else 'issues_detected'
        
        # Send alert if issues found
        if issues:
            message = f"""
AMI Backup Monitoring Alert

Timestamp: {report['timestamp']}
Instance ID: {instance_id}

Issues Detected:
{chr(10).join(issues)}

Primary Region AMIs: {report['primary_ami_count']}
DR Region AMIs: {report['dr_ami_count']}
Latest AMI Age: {report.get('latest_ami_age_hours', 'N/A')} hours
DLM Policies Enabled: {report['dlm_policies_enabled']}
            """
            
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject='⚠️ AMI Backup Alert',
                Message=message
            )
        
        print(json.dumps(report, indent=2))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report)
        }
        
    except Exception as e:
        error_message = f"Error monitoring AMI backups: {str(e)}"
        print(error_message)
        
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject='❌ AMI Monitor Error',
            Message=error_message
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
