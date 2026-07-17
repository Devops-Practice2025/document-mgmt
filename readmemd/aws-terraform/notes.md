**Backend and Frontend image**

```bash
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

export BACKEND_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/bankdocs-dev-backend"
export FRONTEND_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/bankdocs-dev-frontend"
export IMAGE_TAG="v1"

aws ecr get-login-password --region "$AWS_REGION" |
docker login \
  --username AWS \
  --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build \
  --platform linux/amd64 \
  -t "${BACKEND_REPO}:${IMAGE_TAG}" \
  ./backend

docker push "${BACKEND_REPO}:${IMAGE_TAG}"

docker build \
  --platform linux/amd64 \
  -t "${FRONTEND_REPO}:${IMAGE_TAG}" \
  ./frontend/bankdocs-ui

docker push "${FRONTEND_REPO}:${IMAGE_TAG}"

echo
echo "Backend image:"
echo "${BACKEND_REPO}:${IMAGE_TAG}"

echo
echo "Frontend image:"
echo "${FRONTEND_REPO}:${IMAGE_TAG}"
```


