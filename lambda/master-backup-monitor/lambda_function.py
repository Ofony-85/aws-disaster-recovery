import boto3
import json
from datetime import datetime, timedelta

# Initialize AWS clients
rds_primary = boto3.client('rds', region_name='us-east-1')
rds_dr = boto3.client('rds', region_name='us-west-2')
s3_client = boto3.client('s3')
ec2_primary = boto3.client('ec2', region_name='us-east-1')
ec2_dr = boto3.client('ec2', region_name='us-west-2')
dlm_client = boto3.client('dlm', region_name='us-east-1')
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
sns_client = boto3.client('sns', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Master backup monitoring function
    Checks RDS snapshots, S3 replication, AMI backups
    Sends comprehensive report via SNS
    """
    
    config = event.get('config', {})
    db_instance_id = config.get('db_instance_id', 'dr-project-primary-db')
    primary_bucket = config.get('primary_bucket')
    dr_bucket = config.get('dr_bucket')
    instance_id = config.get('instance_id')
    sns_topic_arn = config.get('sns_topic_arn')
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'issues': [],
        'warnings': [],
        'metrics': {}
    }
    
    try:
        # ============================================
        # 1. CHECK RDS BACKUPS
        # ============================================
        print("Checking RDS backups...")
        rds_status = check_rds_backups(db_instance_id)
        report['rds'] = rds_status
        
        if rds_status['issues']:
            report['issues'].extend(rds_status['issues'])
            report['status'] = 'critical'
        
        # ============================================
        # 2. CHECK S3 REPLICATION
        # ============================================
        if primary_bucket and dr_bucket:
            print("Checking S3 replication...")
            s3_status = check_s3_replication(primary_bucket, dr_bucket)
            report['s3'] = s3_status
            
            if s3_status['issues']:
                report['issues'].extend(s3_status['issues'])
                if report['status'] == 'healthy':
                    report['status'] = 'warning'
        
        # ============================================
        # 3. CHECK AMI BACKUPS
        # ============================================
        if instance_id:
            print("Checking AMI backups...")
            ami_status = check_ami_backups(instance_id)
            report['ami'] = ami_status
            
            if ami_status['issues']:
                report['issues'].extend(ami_status['issues'])
                if report['status'] == 'healthy':
                    report['status'] = 'warning'
        
        # ============================================
        # 4. SEND CLOUDWATCH METRICS
        # ============================================
        send_metrics_to_cloudwatch(report)
        
        # ============================================
        # 5. SEND ALERTS IF ISSUES FOUND
        # ============================================
        if report['issues'] or report['warnings']:
            send_alert(report, sns_topic_arn)
        
        # ============================================
        # 6. SEND DAILY SUMMARY (if scheduled)
        # ============================================
        if event.get('send_summary', False):
            send_daily_summary(report, sns_topic_arn)
        
        print(json.dumps(report, indent=2, default=str))
        
        return {
            'statusCode': 200,
            'body': json.dumps(report, default=str)
        }
        
    except Exception as e:
        error_message = f"Error in master backup monitor: {str(e)}"
        print(error_message)
        
        if sns_topic_arn:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject='❌ Master Backup Monitor Error',
                Message=error_message
            )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def check_rds_backups(db_instance_id):
    """Check RDS backup status"""
    status = {
        'primary_snapshots': 0,
        'dr_snapshots': 0,
        'latest_snapshot_age_hours': None,
        'backup_enabled': False,
        'issues': []
    }
    
    try:
        # Check DB instance exists
        db_response = rds_primary.describe_db_instances(
            DBInstanceIdentifier=db_instance_id
        )
        
        db_instance = db_response['DBInstances'][0]
        status['backup_enabled'] = db_instance['BackupRetentionPeriod'] > 0
        
        if not status['backup_enabled']:
            status['issues'].append("❌ RDS automated backups are disabled")
        
        # Get snapshots from primary region
        primary_snapshots = rds_primary.describe_db_snapshots(
            DBInstanceIdentifier=db_instance_id
        )
        status['primary_snapshots'] = len(primary_snapshots['DBSnapshots'])
        
        if status['primary_snapshots'] == 0:
            status['issues'].append("❌ No RDS snapshots found in primary region")
        else:
            # Check latest snapshot age
            latest = max(primary_snapshots['DBSnapshots'], 
                        key=lambda x: x['SnapshotCreateTime'])
            
            age = datetime.now(latest['SnapshotCreateTime'].tzinfo) - latest['SnapshotCreateTime']
            status['latest_snapshot_age_hours'] = age.total_seconds() / 3600
            
            if status['latest_snapshot_age_hours'] > 48:
                status['issues'].append(
                    f"⚠️ Latest RDS snapshot is {status['latest_snapshot_age_hours']:.1f} hours old"
                )
        
        # Get snapshots from DR region
        dr_snapshots = rds_dr.describe_db_snapshots()
        dr_relevant = [s for s in dr_snapshots['DBSnapshots'] 
                      if 'dr' in s['DBSnapshotIdentifier'].lower()]
        status['dr_snapshots'] = len(dr_relevant)
        
        if status['dr_snapshots'] == 0:
            status['issues'].append("⚠️ No RDS snapshots found in DR region")
        
    except Exception as e:
        status['issues'].append(f"❌ Error checking RDS: {str(e)}")
    
    return status

def check_s3_replication(primary_bucket, dr_bucket):
    """Check S3 replication status"""
    status = {
        'replication_enabled': False,
        'primary_objects': 0,
        'dr_objects': 0,
        'replication_difference': 0,
        'versioning_enabled': False,
        'issues': []
    }
    
    try:
        # Check replication configuration
        try:
            replication = s3_client.get_bucket_replication(Bucket=primary_bucket)
            status['replication_enabled'] = True
        except s3_client.exceptions.ReplicationConfigurationNotFoundError:
            status['issues'].append("❌ S3 replication is not configured")
            status['replication_enabled'] = False
        
        # Check versioning
        versioning = s3_client.get_bucket_versioning(Bucket=primary_bucket)
        status['versioning_enabled'] = versioning.get('Status') == 'Enabled'
        
        if not status['versioning_enabled']:
            status['issues'].append("❌ S3 versioning is disabled")
        
        # Count objects
        primary_objects = s3_client.list_objects_v2(Bucket=primary_bucket)
        status['primary_objects'] = primary_objects.get('KeyCount', 0)
        
        dr_objects = s3_client.list_objects_v2(Bucket=dr_bucket)
        status['dr_objects'] = dr_objects.get('KeyCount', 0)
        
        # Check for significant difference
        status['replication_difference'] = abs(
            status['primary_objects'] - status['dr_objects']
        )
        
        if status['replication_difference'] > 10:
            status['issues'].append(
                f"⚠️ Large object count difference: "
                f"Primary={status['primary_objects']}, DR={status['dr_objects']}"
            )
        
    except Exception as e:
        status['issues'].append(f"❌ Error checking S3: {str(e)}")
    
    return status

def check_ami_backups(instance_id):
    """Check AMI backup status"""
    status = {
        'primary_amis': 0,
        'dr_amis': 0,
        'latest_ami_age_hours': None,
        'dlm_enabled': False,
        'issues': []
    }
    
    try:
        # Check DLM policies
        policies = dlm_client.get_lifecycle_policies()
        enabled_policies = [p for p in policies['Policies'] if p['State'] == 'ENABLED']
        status['dlm_enabled'] = len(enabled_policies) > 0
        
        if not status['dlm_enabled']:
            status['issues'].append("❌ No enabled DLM policies found")
        
        # Get AMIs in primary region
        primary_amis = ec2_primary.describe_images(
            Owners=['self'],
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        status['primary_amis'] = len(primary_amis['Images'])
        
        if status['primary_amis'] == 0:
            status['issues'].append("❌ No AMIs found in primary region")
        else:
            # Check latest AMI age
            latest = max(primary_amis['Images'], 
                        key=lambda x: x['CreationDate'])
            
            creation_time = datetime.strptime(
                latest['CreationDate'],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            )
            
            age = datetime.utcnow() - creation_time
            status['latest_ami_age_hours'] = age.total_seconds() / 3600
            
            if status['latest_ami_age_hours'] > 48:
                status['issues'].append(
                    f"⚠️ Latest AMI is {status['latest_ami_age_hours']:.1f} hours old"
                )
        
        # Get AMIs in DR region
        dr_amis = ec2_dr.describe_images(
            Owners=['self'],
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        status['dr_amis'] = len(dr_amis['Images'])
        
        if status['dr_amis'] == 0:
            status['issues'].append("⚠️ No AMIs found in DR region")
        
    except Exception as e:
        status['issues'].append(f"❌ Error checking AMIs: {str(e)}")
    
    return status

def send_metrics_to_cloudwatch(report):
    """Send metrics to CloudWatch"""
    try:
        metrics = []
        
        # RDS metrics
        if 'rds' in report:
            metrics.extend([
                {
                    'MetricName': 'RDSPrimarySnapshots',
                    'Value': report['rds']['primary_snapshots'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'RDSDRSnapshots',
                    'Value': report['rds']['dr_snapshots'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'RDSBackupEnabled',
                    'Value': 1 if report['rds']['backup_enabled'] else 0,
                    'Unit': 'Count'
                }
            ])
            
            if report['rds']['latest_snapshot_age_hours']:
                metrics.append({
                    'MetricName': 'RDSLatestSnapshotAge',
                    'Value': report['rds']['latest_snapshot_age_hours'],
                    'Unit': 'Hours'
                })
        
        # S3 metrics
        if 's3' in report:
            metrics.extend([
                {
                    'MetricName': 'S3ReplicationEnabled',
                    'Value': 1 if report['s3']['replication_enabled'] else 0,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'S3ReplicationDifference',
                    'Value': report['s3']['replication_difference'],
                    'Unit': 'Count'
                }
            ])
        
        # AMI metrics
        if 'ami' in report:
            metrics.extend([
                {
                    'MetricName': 'AMIPrimaryCount',
                    'Value': report['ami']['primary_amis'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'AMIDRCount',
                    'Value': report['ami']['dr_amis'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'DLMEnabled',
                    'Value': 1 if report['ami']['dlm_enabled'] else 0,
                    'Unit': 'Count'
                }
            ])
        
        # Overall health
        metrics.append({
            'MetricName': 'BackupHealthScore',
            'Value': 100 if report['status'] == 'healthy' else 
                    50 if report['status'] == 'warning' else 0,
            'Unit': 'Percent'
        })
        
        # Send to CloudWatch
        for metric in metrics:
            cloudwatch.put_metric_data(
                Namespace='DisasterRecovery/Backups',
                MetricData=[{
                    'MetricName': metric['MetricName'],
                    'Value': metric['Value'],
                    'Unit': metric['Unit'],
                    'Timestamp': datetime.utcnow()
                }]
            )
        
    except Exception as e:
        print(f"Error sending metrics: {str(e)}")

def send_alert(report, sns_topic_arn):
    """Send alert for issues"""
    if not sns_topic_arn:
        return
    
    severity = "🚨 CRITICAL" if report['status'] == 'critical' else "⚠️ WARNING"
    
    message = f"""
{severity} Disaster Recovery Backup Alert

Timestamp: {report['timestamp']}
Overall Status: {report['status'].upper()}

{'='*50}
ISSUES DETECTED:
{'='*50}

{chr(10).join(report['issues'])}

{'='*50}
BACKUP STATUS SUMMARY:
{'='*50}

RDS Backups:
  Primary Snapshots: {report.get('rds', {}).get('primary_snapshots', 'N/A')}
  DR Snapshots: {report.get('rds', {}).get('dr_snapshots', 'N/A')}
  Latest Snapshot Age: {report.get('rds', {}).get('latest_snapshot_age_hours', 'N/A')} hours

S3 Replication:
  Primary Objects: {report.get('s3', {}).get('primary_objects', 'N/A')}
  DR Objects: {report.get('s3', {}).get('dr_objects', 'N/A')}
  Replication Enabled: {report.get('s3', {}).get('replication_enabled', 'N/A')}

AMI Backups:
  Primary AMIs: {report.get('ami', {}).get('primary_amis', 'N/A')}
  DR AMIs: {report.get('ami', {}).get('dr_amis', 'N/A')}
  DLM Enabled: {report.get('ami', {}).get('dlm_enabled', 'N/A')}

Action Required: Please investigate and resolve the issues above.
    """
    
    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject=f'{severity} Backup Status Alert',
            Message=message
        )
    except Exception as e:
        print(f"Error sending alert: {str(e)}")

def send_daily_summary(report, sns_topic_arn):
    """Send daily summary email"""
    if not sns_topic_arn:
        return
    
    status_emoji = {
        'healthy': '✅',
        'warning': '⚠️',
        'critical': '🚨'
    }
    
    message = f"""
{status_emoji.get(report['status'], '❓')} Daily Disaster Recovery Backup Report

Date: {datetime.now().strftime('%Y-%m-%d')}
Overall Status: {report['status'].upper()}

{'='*50}
RDS DATABASE BACKUPS
{'='*50}

Primary Region Snapshots: {report.get('rds', {}).get('primary_snapshots', 0)}
DR Region Snapshots: {report.get('rds', {}).get('dr_snapshots', 0)}
Automated Backups: {'Enabled' if report.get('rds', {}).get('backup_enabled') else 'Disabled'}
Latest Snapshot Age: {report.get('rds', {}).get('latest_snapshot_age_hours', 'N/A')} hours

{'='*50}
S3 BUCKET REPLICATION
{'='*50}

Primary Bucket Objects: {report.get('s3', {}).get('primary_objects', 0)}
DR Bucket Objects: {report.get('s3', {}).get('dr_objects', 0)}
Replication Status: {'Enabled' if report.get('s3', {}).get('replication_enabled') else 'Disabled'}
Versioning: {'Enabled' if report.get('s3', {}).get('versioning_enabled') else 'Disabled'}

{'='*50}
EC2 AMI BACKUPS
{'='*50}

Primary Region AMIs: {report.get('ami', {}).get('primary_amis', 0)}
DR Region AMIs: {report.get('ami', {}).get('dr_amis', 0)}
DLM Policies: {'Active' if report.get('ami', {}).get('dlm_enabled') else 'Inactive'}
Latest AMI Age: {report.get('ami', {}).get('latest_ami_age_hours', 'N/A')} hours

{'='*50}

All backup systems are being monitored continuously.
Next summary report: Tomorrow at the same time.
    """
    
    try:
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject=f'{status_emoji.get(report["status"], "❓")} Daily Backup Report - {datetime.now().strftime("%Y-%m-%d")}',
            Message=message
        )
    except Exception as e:
        print(f"Error sending daily summary: {str(e)}")
