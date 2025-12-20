#!/bin/bash

echo "🔍 Day 3 Verification Report"
echo "=============================="
echo ""

# Read bucket names
PRIMARY_BUCKET=$(cat primary-region/s3/bucket-name.txt)
DR_BUCKET=$(cat dr-region/s3/bucket-name.txt)

echo "📦 1. Primary Bucket Status:"
aws s3api head-bucket --bucket $PRIMARY_BUCKET --region us-east-1 && echo "✅ Exists" || echo "❌ Not found"

echo ""
echo "📦 2. DR Bucket Status:"
aws s3api head-bucket --bucket $DR_BUCKET --region us-west-2 && echo "✅ Exists" || echo "❌ Not found"

echo ""
echo "🔄 3. Versioning Status (Primary):"
aws s3api get-bucket-versioning --bucket $PRIMARY_BUCKET --region us-east-1 --query 'Status'

echo ""
echo "🔄 4. Versioning Status (DR):"
aws s3api get-bucket-versioning --bucket $DR_BUCKET --region us-west-2 --query 'Status'

echo ""
echo "🌍 5. Replication Configuration:"
aws s3api get-bucket-replication \
    --bucket $PRIMARY_BUCKET \
    --region us-east-1 \
    --query 'ReplicationConfiguration.Rules[0].Status'

echo ""
echo "🔐 6. Encryption Status (Primary):"
aws s3api get-bucket-encryption --bucket $PRIMARY_BUCKET --region us-east-1 --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm'

echo ""
echo "📊 7. Object Count (Primary):"
aws s3 ls s3://${PRIMARY_BUCKET}/data/ --recursive --region us-east-1 | wc -l

echo ""
echo "📊 8. Object Count (DR):"
aws s3 ls s3://${DR_BUCKET}/data/ --recursive --region us-west-2 | wc -l

echo ""
echo "⚡ 9. Lambda Function Status:"
aws lambda get-function \
    --function-name dr-s3-replication-monitor \
    --query 'Configuration.State' \
    --region us-east-1

echo ""
echo "⏰ 10. EventBridge Rule:"
aws events describe-rule \
    --name dr-s3-replication-check \
    --query 'State' \
    --region us-east-1

echo ""
echo "=============================="
echo "✅ Day 3 Complete!"
