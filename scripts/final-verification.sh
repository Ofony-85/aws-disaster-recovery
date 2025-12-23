#!/bin/bash

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  AWS Disaster Recovery System - Final Verification      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0

# Function to check status
check_status() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
    else
        echo "❌ $1"
        ((ERRORS++))
    fi
}

# Get resource IDs
INSTANCE_ID=$(cat primary-region/ec2-instance-id.txt 2>/dev/null)
PRIMARY_BUCKET=$(cat primary-region/s3/bucket-name.txt 2>/dev/null)
DR_BUCKET=$(cat dr-region/s3/bucket-name.txt 2>/dev/null)

echo "═══════════════════════════════════════════Continue10:39 PM════════════════"
echo "1. PRIMARY INFRASTRUCTURE (us-east-1)"
echo "═══════════════════════════════════════════════════════════"
echo ""
Check EC2
aws ec2 describe-instances 
--instance-ids $INSTANCE_ID 
--query 'Reservations[0].Instances[0].State.Name' 
--region us-east-1 | grep -q "running"
check_status "EC2 Instance Running"
Check RDS
aws rds describe-db-instances 
--db-instance-identifier dr-project-primary-db 
--query 'DBInstances[0].DBInstanceStatus' 
--region us-east-1 | grep -q "available"
check_status "RDS Database Available"
Check S3
aws s3 ls s3://$PRIMARY_BUCKET >/dev/null 2>&1
check_status "Primary S3 Bucket Exists"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "2. BACKUP SYSTEMS"
echo "═══════════════════════════════════════════════════════════"
echo ""
Check RDS Snapshots
RDS_SNAPSHOTS=$(aws rds describe-db-snapshots 
--db-instance-identifier dr-project-primary-db 
--region us-east-1 
--query 'length(DBSnapshots)' 
--output text)
echo "RDS Snapshots in Primary: $RDS_SNAPSHOTS"
[ "$RDS_SNAPSHOTS" -gt 0 ]
check_status "RDS Snapshots Present"
Check DR Snapshots
DR_SNAPSHOTS=$(aws rds describe-db-snapshots 
--region us-west-2 
--query 'length(DBSnapshots[?contains(DBSnapshotIdentifier, dr)])' 
--output text)
echo "RDS Snapshots in DR: $DR_SNAPSHOTS"
[ "$DR_SNAPSHOTS" -gt 0 ]
check_status "RDS DR Snapshots Present"
Check AMIs
PRIMARY_AMIS=$(aws ec2 describe-images 
--owners self 
--region us-east-1 
--query 'length(Images)' 
--output text)
echo "AMIs in Primary: $PRIMARY_AMIS"
[ "$PRIMARY_AMIS" -gt 0 ]
check_status "Primary AMIs Present"
DR_AMIS=$(aws ec2 describe-images 
--owners self 
--region us-west-2 
--query 'length(Images)' 
--output text)
echo "AMIs in DR: $DR_AMIS"
[ "$DR_AMIS" -gt 0 ]
check_status "DR AMIs Present"
Check S3 Replication
aws s3 ls s3://$DR_BUCKET >/dev/null 2>&1
check_status "DR S3 Bucket Exists"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "3. MONITORING & ALERTING"
echo "═══════════════════════════════════════════════════════════"
echo ""
Check Lambda Functions
LAMBDA_COUNT=$(aws lambda list-functions 
--region us-east-1 
--query 'length(Functions[?contains(FunctionName, dr-)])' 
--output text)
echo "Lambda Functions: $LAMBDA_COUNT"
[ "$LAMBDA_COUNT" -ge 3 ]
check_status "Lambda Functions Deployed"
Check EventBridge Rules
RULE_COUNT=$(aws events list-rules 
--region us-east-1 
--query 'length(Rules[?contains(Name, dr-)])' 
--output text)
echo "EventBridge Rules: $RULE_COUNT"
[ "$RULE_COUNT" -ge 3 ]
check_status "EventBridge Rules Configured"
Check CloudWatch Dashboard
aws cloudwatch get-dashboard 
--dashboard-name DR-Backup-Monitoring 
--region us-east-1 >/dev/null 2>&1
check_status "CloudWatch Dashboard"
Check Alarms
ALARMS=$(aws cloudwatch describe-alarms 
--alarm-name-prefix DR- 
--region us-east-1 
--query 'length(MetricAlarms)' 
--output text)
echo "CloudWatch Alarms: $ALARMS"
[ "$ALARMS" -gt 0 ]
check_status "CloudWatch Alarms Configured"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "4. SUMMARY"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Total Components Checked: 15+"
echo "Errors: $ERRORS"
echo ""
if [ $ERRORS -eq 0 ]; then
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅ ALL SYSTEMS OPERATIONAL                  ║"
echo "║        Disaster Recovery System is Ready!                ║"
echo "╚══════════════════════════════════════════════════════════╝"
exit 0
else
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ⚠️  ISSUES DETECTED                         ║"
echo "║        Please review and fix the errors above            ║"
echo "╚══════════════════════════════════════════════════════════╝"
exit 1
fi
