#!/bin/bash

echo "🧪 Testing EC2 Restore Capability"
echo "=================================="
echo ""

cd ~/aws-disaster-recovery

aws lambda invoke \
    --function-name dr-ec2-restore-tester \
    --payload file://ec2-test-config.json \
    --region us-east-1 \
    response.json

echo ""
cat response.json | jq '.'

echo ""
echo "✅ EC2 restore test initiated"
echo "Check your email for results in 5-10 minutes"
