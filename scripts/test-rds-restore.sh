#!/bin/bash

echo "🧪 Testing RDS Restore Capability"
echo "=================================="
echo ""

cd ~/aws-disaster-recovery

aws lambda invoke \
    --function-name dr-rds-restore-tester \
    --payload file://rds-test-config.json \
    --region us-east-1 \
    response.json

echo ""
cat response.json | jq '.'

echo ""
echo "✅ RDS restore test initiated"
echo "Check your email for results in 10-15 minutes"
