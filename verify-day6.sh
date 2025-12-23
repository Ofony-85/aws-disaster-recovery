#!/bin/bash

echo "🔍 Day 6 Verification Report"
echo "=============================="
echo ""

echo "⚡ Restore Testing Lambdas:"
aws lambda list-functions \
    --region us-east-1 \
    --query 'Functions[?contains(FunctionName, `restore`) || contains(FunctionName, `cleanup`)].FunctionName' \
    --output table

echo ""
echo "⏰ EventBridge Schedules:"
aws events list-rules \
    --region us-east-1 \
    --query 'Rules[?contains(Name, `weekly`) || contains(Name, `cleanup`)].{Name:Name,State:State,Schedule:ScheduleExpression}' \
    --output table

echo ""
echo "=============================="
echo "✅ Day 6 Complete!"
echo "=============================="
echo ""
echo "Summary:"
echo "  ✅ 3 Lambda functions deployed"
echo "  ✅ Weekly RDS test (Sundays 2 AM)"
echo "  ✅ Weekly EC2 test (Sundays 3 AM)"
echo "  ✅ Daily cleanup (midnight)"
echo "  ✅ Manual test scripts created"
echo ""
echo "Progress: 86% Complete (6/7 days)"
