#!/bin/bash

# Update RAG Service Script
# Usage: ./update.sh <organization_name> <project_id> [image_tag]

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ $# -lt 2 ]; then
    print_error "Usage: $0 <organization_name> <project_id> [image_tag]"
    exit 1
fi

ORGANIZATION_NAME=$1
PROJECT_ID=$2
IMAGE_TAG=${3:-latest}

print_status "Updating service for organization: $ORGANIZATION_NAME"

# Build new image
IMAGE_NAME="gcr.io/$PROJECT_ID/$ORGANIZATION_NAME-rag-agent:$IMAGE_TAG"

print_status "Building new Docker image..."
docker build -t $IMAGE_NAME .

print_status "Pushing image..."
docker push $IMAGE_NAME

print_status "Updating Cloud Run service..."
gcloud run deploy $ORGANIZATION_NAME-rag-agent \
    --image $IMAGE_NAME \
    --region us-central1 \
    --platform managed

print_success "Service updated successfully!"