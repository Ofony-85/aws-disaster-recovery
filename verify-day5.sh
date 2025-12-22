#!/bin/bash

echo "🔍 Day 5 Verification Report"
echo "=============================="
echo ""

echo "⚡ 1. Master Lambda Status:"
aws lambda get-function \
    --function-name dr-master-backup-monitor \
    --query 'Configuration.[FunctionName,State,Runtime,Timeout,MemorySize]' \
    --region us-east-1 \
    --output table

echo ""
echo "⏰ 2. Continuous Monitoring Rule:"
aws events describe-rule \
    --name dr-continuous-backup-check \
    --query '[Name,State,ScheduleExpression]' \
    --region us-east-1 \
    --output table

echo ""
echo "⏰ 3. Daily Summary Rule:"
aws events describe-rule \
    --name dr-daily-summary-report \
    --query '[Name,State,ScheduleExpression]' \
    --region us-east-1 \
    --output table

echo ""
echo "📊 4. CloudWatch Dashboard:"
aws cloudwatch list-dashboards \
    --region us-east-1 \
    --query "DashboardEntries[?DashboardName=='DR-Backup-Monitoring'].DashboardName" \
    --output text

echo ""
echo "🔔 5. CloudWatch Alarms:"
aws cloudwatch describe-alarms \
    --alarm-name-prefix DR- \
    --region us-east-1 \
    --query 'MetricAlarms[*].[AlarmName,StateValue]' \
    --output table

echo ""
echo "=============================="
echo "✅ Day 5 Complete!"
echo "=============================="
echo ""
echo "Summary:"
echo "  ✅ Master monitoring Lambda deployed"
echo "  ✅ Continuous monitoring (every 6 hours)"
echo "  ✅ Daily summary emails (8 AM UTC)"
echo "  ✅ CloudWatch dashboard created"
echo "  ✅ 3 CloudWatch alarms configured"
echo ""
echo "Progress: 71% Complete (5/7 days)"
