import boto3
import json
from datetime import datetime

def lambda_handler(event, context):
    """
    Automatically copy RDS snapshots from us-east-1 to us-west-2
    """
    
    # Initialize clients
    rds_primary = boto3.client('rds', region_name='us-east-1')
    rds_dr = boto3.client('rds', region_name='us-west-2')
    
    db_instance_id = 'dr-project-primary-db'
    
    try:
        # Get the latest automated snapshot
        response = rds_primary.describe_db_snapshots(
            DBInstanceIdentifier=db_instance_id,
            SnapshotType='automated',
            MaxRecords=1
        )
        
        if not response['DBSnapshots']:
            return {
                'statusCode': 404,
                'body': json.dumps('No snapshots found')
            }
        
        latest_snapshot = response['DBSnapshots'][0]
        source_snapshot_arn = latest_snapshot['DBSnapshotArn']
        source_snapshot_id = latest_snapshot['DBSnapshotIdentifier']
        
        # Create DR snapshot identifier
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        dr_snapshot_id = f"dr-copy-{timestamp}"
        
        # Copy snapshot to DR region
        rds_dr.copy_db_snapshot(
            SourceDBSnapshotIdentifier=source_snapshot_arn,
            TargetDBSnapshotIdentifier=dr_snapshot_id,
            SourceRegion='us-east-1',
            CopyTags=True
        )
        
        print(f"✅ Snapshot copied: {source_snapshot_id} -> {dr_snapshot_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Snapshot copied successfully',
                'source': source_snapshot_id,
                'destination': dr_snapshot_id
            })
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
