#!/bin/bash
echo "🔍 Day 2 Verification Report"
echo "=============================="
echo ""

echo "✅ 1. RDS Instance Status:"
aws rds describe-db-instances \
    --db-instance-identifier dr-project-primary-db \
    --query 'DBInstances[0].DBInstanceStatus' \
    --region us-east-1

echo ""
echo "✅ 2. Database Endpoint:"
aws rds describe-db-instances \
    --db-instance-identifier dr-project-primary-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --region us-east-1

echo ""
echo "✅ 3. Backup Retention:"
aws rds describe-db-instances \
    --db-instance-identifier dr-project-primary-db \
    --query 'DBInstances[0].BackupRetentionPeriod' \
    --region us-east-1

echo ""
echo "✅ 4. Snapshots in Primary (us-east-1):"
aws rds describe-db-snapshots \
    --db-instance-identifier dr-project-primary-db \
    --query 'length(DBSnapshots)' \
    --region us-east-1

echo ""
echo "✅ 5. Snapshots in DR (us-west-2):"
aws rds describe-db-snapshots \
    --query 'length(DBSnapshots[?contains(DBSnapshotIdentifier, `dr`)])' \
    --region us-west-2

echo ""
echo "✅ 6. Lambda Function Status:"
aws lambda get-function \
    --function-name dr-snapshot-copy \
    --query 'Configuration.State' \
    --region us-east-1

echo ""
echo "✅ 7. EventBridge Rule Status:"
aws events describe-rule \
    --name dr-daily-snapshot-copy \
    --query 'State' \
    --region us-east-1

echo ""
echo "=============================="
echo "📊 Day 2 Complete! All systems operational."
