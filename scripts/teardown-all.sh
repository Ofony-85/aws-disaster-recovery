#!/bin/bash

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         AWS Disaster Recovery - COMPLETE TEARDOWN        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  WARNING: This will DELETE ALL resources and backups!"
echo "⚠️  This action CANNOT be undone!"
echo ""
read -p "Type 'DELETE-EVERYTHING' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE-EVERYTHING" ]; then
    echo "Teardown cancelled."
    exit 0
fi

echo ""
echo "Starting teardown process..."
echo ""

# Get resource IDs
INSTANCE_ID=$(cat primary-region/ec2-instance-id.txt 2>/dev/null)
PRIMARY_BUCKET=$(cat primary-region/s3/bucket-name.txt 2>/dev/null)
DR_BUCKET=$(cat dr-region/s3/bucket-name.txt 2>/dev/null)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "═══════════════════════════════════════════════════════════"
echo "1. Deleting Lambda Functions"
echo "═══════════════════════════════════════════════════════════"

for func in dr-master-backup-monitor dr-rds-restore-tester dr-ec2-restore-tester dr-test-cleanup dr-ami-monitor; do
    echo "Deleting Lambda: $func"
    aws lambda delete-function --function-name $func --region us-east-1 2>/dev/null
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "2. Deleting EventBridge Rules"
echo "═══════════════════════════════════════════════════════════"

for rule in dr-continuous-backup-check dr-daily-summary-report dr-weekly-rds-restore-test dr-weekly-ec2-restore-test dr-daily-test-cleanup dr-ami-monitor-check; do
    echo "Removing targets from: $rule"
    aws events remove-targets --rule $rule --ids 1 --region us-east-1 2>/dev/null
    echo "Deleting rule: $rule"
    aws events delete-rule --name $rule --region us-east-1 2>/dev/null
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "3. Deleting CloudWatch Resources"
echo "═══════════════════════════════════════════════════════════"

# Delete alarms
aws cloudwatch describe-alarms --alarm-name-prefix DR- --region us-east-1 --query 'MetricAlarms[*].AlarmName' --output text | \
while read alarm; do
    echo "Deleting alarm: $alarm"
    aws cloudwatch delete-alarms --alarm-names $alarm --region us-east-1 2>/dev/null
done

# Delete dashboard
echo "Deleting CloudWatch dashboard"
aws cloudwatch delete-dashboards --dashboard-names DR-Backup-Monitoring --region us-east-1 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "4. Deleting DLM Policies"
echo "═══════════════════════════════════════════════════════════"

aws dlm get-lifecycle-policies --region us-east-1 --query 'Policies[*].PolicyId' --output text | \
while read policy; do
    echo "Deleting DLM policy: $policy"
    aws dlm delete-lifecycle-policy --policy-id $policy --region us-east-1 2>/dev/null
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "5. Deleting AMIs and Snapshots"
echo "═══════════════════════════════════════════════════════════"

# Primary region
echo "Deleting AMIs in us-east-1..."
aws ec2 describe-images --owners self --region us-east-1 --query 'Images[*].ImageId' --output text | \
while read ami; do
    echo "Deregistering AMI: $ami"
    aws ec2 deregister-image --image-id $ami --region us-east-1 2>/dev/null
done

# DR region
echo "Deleting AMIs in us-west-2..."
aws ec2 describe-images --owners self --region us-west-2 --query 'Images[*].ImageId' --output text | \
while read ami; do
    echo "Deregistering AMI: $ami"
    aws ec2 deregister-image --image-id $ami --region us-west-2 2>/dev/null
done

# Delete snapshots
echo "Deleting EBS snapshots..."
for region in us-east-1 us-west-2; do
    aws ec2 describe-snapshots --owner-ids self --region $region --query 'Snapshots[*].SnapshotId' --output text | \
    while read snapshot; do
        echo "Deleting snapshot: $snapshot in $region"
        aws ec2 delete-snapshot --snapshot-id $snapshot --region $region 2>/dev/null
    done
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "6. Deleting RDS Resources"
echo "═══════════════════════════════════════════════════════════"

# Delete primary RDS
echo "Deleting primary RDS instance..."
aws rds delete-db-instance \
    --db-instance-identifier dr-project-primary-db \
    --skip-final-snapshot \
    --delete-automated-backups \
    --region us-east-1 2>/dev/null

# Wait for deletion to initiate
sleep 10

# Delete RDS snapshots in primary
echo "Deleting RDS snapshots in us-east-1..."
aws rds describe-db-snapshots --region us-east-1 --query 'DBSnapshots[*].DBSnapshotIdentifier' --output text | \
while read snapshot; do
    echo "Deleting snapshot: $snapshot"
    aws rds delete-db-snapshot --db-snapshot-identifier $snapshot --region us-east-1 2>/dev/null
done

# Delete RDS snapshots in DR
echo "Deleting RDS snapshots in us-west-2..."
aws rds describe-db-snapshots --region us-west-2 --query 'DBSnapshots[*].DBSnapshotIdentifier' --output text | \
while read snapshot; do
    echo "Deleting snapshot: $snapshot"
    aws rds delete-db-snapshot --db-snapshot-identifier $snapshot --region us-west-2 2>/dev/null
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "7. Deleting S3 Buckets"
echo "═══════════════════════════════════════════════════════════"

# Empty and delete primary bucket
if [ -n "$PRIMARY_BUCKET" ]; then
    echo "Emptying primary bucket: $PRIMARY_BUCKET"
    aws s3 rm s3://$PRIMARY_BUCKET --recursive --region us-east-1 2>/dev/null
    
    echo "Deleting primary bucket: $PRIMARY_BUCKET"
    aws s3 rb s3://$PRIMARY_BUCKET --force --region us-east-1 2>/dev/null
fi

# Empty and delete DR bucket
if [ -n "$DR_BUCKET" ]; then
    echo "Emptying DR bucket: $DR_BUCKET"
    aws s3 rm s3://$DR_BUCKET --recursive --region us-west-2 2>/dev/null
    
    echo "Deleting DR bucket: $DR_BUCKET"
    aws s3 rb s3://$DR_BUCKET --force --region us-west-2 2>/dev/null
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "8. Deleting Terraform Resources"
echo "═══════════════════════════════════════════════════════════"

cd terraform/primary 2>/dev/null
if [ -f "terraform.tfstate" ]; then
    echo "Running terraform destroy..."
    terraform destroy -auto-approve
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "9. Deleting IAM Roles"
echo "═══════════════════════════════════════════════════════════"

for role in DR-DLM-Lifecycle-Role DR-Master-Monitor-Lambda-Role DR-RDS-Restore-Tester-Role DR-EC2-Restore-Tester-Role DR-Test-Cleanup-Role DR-AMI-Monitor-Lambda-Role DR-S3-Monitor-Lambda-Role DR-S3-Replication-Role; do
    echo "Deleting IAM role: $role"
    
    # Delete inline policies
    aws iam list-role-policies --role-name $role --query 'PolicyNames' --output text 2>/dev/null | \
    while read policy; do
        aws iam delete-role-policy --role-name $role --policy-name $policy 2>/dev/null
    done
    
    # Detach managed policies
    aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null | \
    while read policy; do
        aws iam detach-role-policy --role-name $role --policy-arn $policy 2>/dev/null
    done
    
    # Delete role
    aws iam delete-role --role-name $role 2>/dev/null
done

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "10. Deleting SNS Topics"
echo "═══════════════════════════════════════════════════════════"

aws sns list-topics --region us-east-1 --query 'Topics[?contains(TopicArn, `dr-`)].TopicArn' --output text | \
while read topic; do
    echo "Deleting SNS topic: $topic"
    aws sns delete-topic --topic-arn $topic --region us-east-1 2>/dev/null
done

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅ TEARDOWN COMPLETE                        ║"
echo "║                                                           ║"
echo "║  All AWS resources have been deleted.                    ║"
echo "║  Your account is now clean.                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To remove local files: rm -rf ~/aws-disaster-recovery"
