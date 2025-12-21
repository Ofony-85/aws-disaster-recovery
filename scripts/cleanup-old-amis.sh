#!/bin/bash

# Script to clean up AMIs older than retention period
# This supplements DLM's cleanup

RETENTION_DAYS=7
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🧹 Cleaning up AMIs older than ${RETENTION_DAYS} days"
echo "================================================="

# Calculate cutoff date
CUTOFF_DATE=$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%dT%H:%M:%S.000Z)

# Get old AMIs in primary region
echo "Checking us-east-1..."
OLD_AMIS=$(aws ec2 describe-images \
    --owners $ACCOUNT_ID \
    --query "Images[?CreationDate<\`${CUTOFF_DATE}\`].[ImageId,Name,CreationDate]" \
    --output text \
    --region us-east-1)

if [ -n "$OLD_AMIS" ]; then
    echo "Found old AMIs to delete:"
    echo "$OLD_AMIS"
    
    echo "$OLD_AMIS" | while read ami_id name creation_date; do
        echo "Deregistering AMI: $ami_id ($name)"
        
        # Get associated snapshots
        SNAPSHOTS=$(aws ec2 describe-images \
            --image-ids $ami_id \
            --query 'Images[0].BlockDeviceMappings[*].Ebs.SnapshotId' \
            --output text \
            --region us-east-1)
        
        # Deregister AMI
        aws ec2 deregister-image \
            --image-id $ami_id \
            --region us-east-1
        
        # Delete associated snapshots
        for snapshot in $SNAPSHOTS; do
            echo "Deleting snapshot: $snapshot"
            aws ec2 delete-snapshot \
                --snapshot-id $snapshot \
                --region us-east-1
        done
    done
else
    echo "No old AMIs found in us-east-1"
fi

# Repeat for DR region
echo ""
echo "Checking us-west-2..."
OLD_AMIS_DR=$(aws ec2 describe-images \
    --owners $ACCOUNT_ID \
    --query "Images[?CreationDate<\`${CUTOFF_DATE}\`].[ImageId,Name,CreationDate]" \
    --output text \
    --region us-west-2)

if [ -n "$OLD_AMIS_DR" ]; then
    echo "Found old AMIs to delete:"
    echo "$OLD_AMIS_DR"
    
    echo "$OLD_AMIS_DR" | while read ami_id name creation_date; do
        echo "Deregistering AMI: $ami_id ($name)"
        
        SNAPSHOTS=$(aws ec2 describe-images \
            --image-ids $ami_id \
            --query 'Images[0].BlockDeviceMappings[*].Ebs.SnapshotId' \
            --output text \
            --region us-west-2)
        
        aws ec2 deregister-image \
            --image-id $ami_id \
            --region us-west-2
        
        for snapshot in $SNAPSHOTS; do
            echo "Deleting snapshot: $snapshot"
            aws ec2 delete-snapshot \
                --snapshot-id $snapshot \
                --region us-west-2
        done
    done
else
    echo "No old AMIs found in us-west-2"
fi

echo ""
echo "✅ Cleanup complete!"
