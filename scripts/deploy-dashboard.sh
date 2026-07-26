#!/usr/bin/env bash
set -euo pipefail

AWS_ACCOUNT_ID="013523127218"
AWS_REGION="us-east-1"
SERVICE_NAME="anchoralpha-dashboard"
S3_BUCKET="anchor-alpha-momentum-data-prod-${AWS_ACCOUNT_ID}"

echo "==> Building Streamlit Docker image (linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile.streamlit -t anchoralpha-dashboard .

echo "==> Pushing image to Lightsail..."
PUSH_OUTPUT=$(aws lightsail push-container-image \
    --region "$AWS_REGION" \
    --service-name "$SERVICE_NAME" \
    --label dashboard \
    --image anchoralpha-dashboard:latest 2>&1)
echo "$PUSH_OUTPUT"

IMAGE=$(echo "$PUSH_OUTPUT" | grep -o ':[a-zA-Z0-9._-]*dashboard\.[a-zA-Z0-9._-]*\.[0-9]*' | tail -1)
if [ -z "$IMAGE" ]; then
    echo "ERROR: Could not capture image name from push output"
    exit 1
fi
echo "==> Lightsail image: $IMAGE"

# Read credentials from env or fall back to ~/.aws/credentials [default]
if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
    AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
fi
if [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
fi

# Read admin password from Secrets Manager (anchoralpha/dashboard → ADMIN_PASSWORD field)
echo "==> Reading admin password from Secrets Manager..."
ADMIN_PASSWORD=$(aws secretsmanager get-secret-value \
    --region "$AWS_REGION" \
    --secret-id "anchoralpha/dashboard" \
    --query SecretString \
    --output text 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ADMIN_PASSWORD',''))" 2>/dev/null || echo "")
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "WARNING: Could not read ADMIN_PASSWORD from anchoralpha/dashboard — admin features will be disabled"
fi

echo "==> Creating deployment..."
aws lightsail create-container-service-deployment \
    --region "$AWS_REGION" \
    --service-name "$SERVICE_NAME" \
    --containers "{
        \"dashboard\": {
            \"image\": \"$IMAGE\",
            \"ports\": {\"8501\": \"HTTP\"},
            \"environment\": {
                \"AWS_DEFAULT_REGION\": \"$AWS_REGION\",
                \"AWS_REGION\": \"$AWS_REGION\",
                \"AWS_ACCESS_KEY_ID\": \"$AWS_ACCESS_KEY_ID\",
                \"AWS_SECRET_ACCESS_KEY\": \"$AWS_SECRET_ACCESS_KEY\",
                \"ENVIRONMENT\": \"prod\",
                \"S3_BUCKET\": \"$S3_BUCKET\",
                \"ADMIN_PASSWORD\": \"$ADMIN_PASSWORD\"
            }
        }
    }" \
    --public-endpoint '{
        "containerName": "dashboard",
        "containerPort": 8501,
        "healthCheck": {
            "healthyThreshold": 2,
            "unhealthyThreshold": 2,
            "timeoutSeconds": 2,
            "intervalSeconds": 5,
            "path": "/_stcore/health",
            "successCodes": "200-499"
        }
    }'

echo "==> Deployment triggered. Check status at:"
echo "    https://lightsail.aws.amazon.com/ls/webapp/us-east-1/container-services/$SERVICE_NAME/deployments"
