import boto3
import json
from datetime import datetime

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

def lambda_handler(event, context):
    """
    Monitor S3 replication status and send alerts if replication fails
    """
    
    primary_bucket = event['primary_bucket']
    dr_bucket = event['dr_bucket']
    sns_topic_arn = event['sns_topic_arn']
    
    issues = []
    
    try:
        # Check if replication is enabled
        replication_config = s3_client.get_bucket_replication(Bucket=primary_bucket)
        
        if not replication_config['ReplicationConfiguration']['Rules'][0]['Status'] == 'Enabled':
            issues.append("❌ Replication is not enabled")
        
        # Get replication metrics
        primary_objects = s3_client.list_objects_v2(Bucket=primary_bucket)
        dr_objects = s3_client.list_objects_v2(Bucket=dr_bucket)
        
        primary_count = primary_objects.get('KeyCount', 0)
        dr_count = dr_objects.get('KeyCount', 0)
        
        # Check if counts match (allowing for replication delay)
        if abs(primary_count - dr_count) > 5:
            issues.append(f"⚠️ Object count mismatch: Primary={primary_count}, DR={dr_count}")
        
        # Prepare report
        report = {
            'timestamp': datetime.now().isoformat(),
            'primary_bucket': primary_bucket,
            'dr_bucket': dr_bucket,
            'primary_object_count': primary_count,
            'dr_object_count': dr_count,
            'replication_enabled': True,
            'issues': issues
        }
        
        # Send alert if issues found
        if issues:
            message = f"""
S3 Replication Monitoring Alert

Timestamp: {report['timestamp']}
Primary Bucket: {primary_bucket}
DR Bucket: {dr_bucket}

Issues Detected:
{chr(10).join(issues)}

Primary Object Count: {primary_count}
DR Object Count: {dr_count}
            """
            
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject='⚠️ S3 Replication Alert',
                Message=message
            )
        
        print(json.dumps(report, indent=2))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report)
        }
        
    except Exception as e:
        error_message = f"Error monitoring replication: {str(e)}"
        print(error_message)
        
        # Send error alert
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject='❌ S3 Replication Monitor Error',
            Message=error_message
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
