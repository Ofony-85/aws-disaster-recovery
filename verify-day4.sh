#!/bin/bash

echo "🔍 Day 4 Verification Report"
echo "=============================="
echo ""

INSTANCE_ID=$(cat primary-region/ec2-instance-id.txt 2>/dev/null)
POLICY_ID=$(cat primary-region/dlm-policy-id.txt 2>/dev/null)

echo "🖥️  1. EC2 Instance Status:"
aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].State.Name' \
    --region us-east-1

echo ""
echo "🏷️  2. Instance Backup Tag:"
aws ec2 describe-tags \
    --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=Backup" \
    --query 'Tags[0].Value' \
    --region us-east-1

echo ""
echo "📋 3. DLM Policy Status:"
aws dlm get-lifecycle-policy \
    --policy-id $POLICY_ID \
    --query 'Policy.State' \
    --region us-east-1 2>/dev/null || echo "Not found (check primary-region/dlm-policy-id.txt)"

echo ""
echo "📸 4. AMIs in Primary Region:"
aws ec2 describe-images \
    --owners self \
    --query 'length(Images)' \
    --region us-east-1

echo ""
echo "📸 5. AMIs in DR Region:"
aws ec2 describe-images \
    --owners self \
    --query 'length(Images)' \
    --region us-west-2

echo ""
echo "📸 6. Recent AMIs (Primary):"
aws ec2 describe-images \
    --owners self \
    --query 'Images[*].[ImageId,Name,CreationDate]' \
    --output table \
    --region us-east-1 | head -20

echo ""
echo "⚡ 7. Lambda Function Status (if exists):"
aws lambda get-function \
    --function-name dr-ami-monitor \
    --query 'Configuration.State' \
    --region us-east-1 2>/dev/null || echo "Skipped (covered by master monitor)"

echo ""
echo "⏰ 8. EventBridge Rule:"
aws events describe-rule \
    --name dr-ami-monitor-check \
    --query 'State' \
    --region us-east-1 2>/dev/null || echo "Not applicable"

echo ""
echo "=============================="
echo "✅ Day 4 Complete!"
