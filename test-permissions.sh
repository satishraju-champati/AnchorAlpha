#!/bin/bash

echo "🧪 Testing AWS Permissions for Deployment"
echo "=========================================="

echo "1. Testing CloudFormation access..."
aws cloudformation list-stacks --max-items 1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ CloudFormation: PASS"
else
    echo "   ❌ CloudFormation: FAIL"
fi

echo "2. Testing Lambda access..."
aws lambda list-functions --max-items 1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Lambda: PASS"
else
    echo "   ❌ Lambda: FAIL"
fi

echo "3. Testing S3 access..."
aws s3 ls > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ S3: PASS"
else
    echo "   ❌ S3: FAIL"
fi

echo "4. Testing IAM access..."
aws iam list-roles --max-items 1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ IAM: PASS"
else
    echo "   ❌ IAM: FAIL"
fi

echo ""
echo "🎯 Summary:"
echo "If all tests pass, you're ready for deployment!"
echo "If any fail, add the missing permissions in AWS Console."