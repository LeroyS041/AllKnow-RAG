#!/bin/bash
# GCP Deployment Script

set -e

PROJECT_ID="YOUR_PROJECT_ID"
REGION="us-central1"
CLUSTER_NAME="AllKnow-cluster"

echo "🚀 Deploying to GCP..."

# 1. Build and push to GCR
echo "📦 Building Docker image..."
cd backend
docker build -t gcr.io/$PROJECT_ID/AllKnow-backend:latest .

echo "⬆️  Pushing to GCR..."
docker push gcr.io/$PROJECT_ID/AllKnow-backend:latest

# 2. Update K8s deployment
echo "☸️  Deploying to GKE..."
kubectl set image deployment/AllKnow-backend \
  backend=gcr.io/$PROJECT_ID/AllKnow-backend:latest \
  -n AllKnow

echo "✅ Deployment complete!"
kubectl get svc AllKnow-backend -n AllKnow
