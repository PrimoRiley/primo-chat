#!/bin/bash

# Multi-Organization RAG Deployment Script
# Usage: ./deploy.sh <organization_name> <project_id> <openai_api_key> [region]

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate input parameters
if [ $# -lt 3 ]; then
    print_error "Usage: $0 <organization_name> <project_id> <openai_api_key> [region]"
    echo "Example: $0 acme-corp my-gcp-project-123 sk-your-api-key us-central1"
    exit 1
fi

ORGANIZATION_NAME=$1
PROJECT_ID=$2
OPENAI_API_KEY=$3
REGION=${4:-us-central1}

# Validate organization name format
if [[ ! $ORGANIZATION_NAME =~ ^[a-z0-9-]+$ ]]; then
    print_error "Organization name must contain only lowercase letters, numbers, and hyphens"
    exit 1
fi

print_status "Starting deployment for organization: $ORGANIZATION_NAME"
print_status "Project ID: $PROJECT_ID"
print_status "Region: $REGION"

# Check required tools
print_status "Checking required tools..."

if ! command_exists gcloud; then
    print_error "Google Cloud SDK (gcloud) is not installed"
    exit 1
fi

if ! command_exists docker; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command_exists terraform; then
    print_error "Terraform is not installed"
    exit 1
fi

print_success "All required tools are available"

# Set the GCP project
print_status "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
print_status "Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com \
                      secretmanager.googleapis.com \
                      storage.googleapis.com \
                      cloudbuild.googleapis.com \
                      containerregistry.googleapis.com

print_success"APIs enabled successfully"

# Build and push Docker image
print_status "Building Docker image..."
IMAGE_NAME="gcr.io/$PROJECT_ID/$ORGANIZATION_NAME-rag-agent:latest"

docker build -t $IMAGE_NAME .

print_status "Pushing image to Google Container Registry..."
docker push $IMAGE_NAME

print_success "Docker image built and pushed successfully"

# Deploy infrastructure with Terraform
print_status "Deploying infrastructure with Terraform..."

cd terraform

# Create terraform.tfvars if it doesn't exist
if [ ! -f terraform.tfvars ]; then
    print_status "Creating terraform.tfvars..."
    cat > terraform.tfvars <<EOF
organization_name = "$ORGANIZATION_NAME"
project_id       = "$PROJECT_ID"
openai_api_key   = "$OPENAI_API_KEY"
region           = "$REGION"
EOF
fi

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan deployment
print_status "Planning Terraform deployment..."
terraform plan

# Apply deployment
print_status "Applying Terraform deployment..."
terraform apply -auto-approve

# Get outputs
SERVICE_URL=$(terraform output -raw service_url)
DATA_BUCKET=$(terraform output -raw data_bucket)

cd ..

print_success "Infrastructure deployed successfully!"

# Wait for service to be ready
print_status "Waiting for Cloud Run service to be ready..."
sleep 30

# Test the deployment
print_status "Testing deployment..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    print_success "Deployment test successful!"
else
    print_warning "Deployment test returned HTTP $HTTP_STATUS. Service may still be starting up."
fi

# Display deployment information
echo ""
echo "=================================="
print_success "DEPLOYMENT COMPLETED SUCCESSFULLY"
echo "=================================="
echo ""
echo "Organization: $ORGANIZATION_NAME"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Data Bucket: $DATA_BUCKET"
echo ""
echo "Next Steps:"
echo "1. Visit the service URL to access your RAG assistant"
echo "2. Upload documents to build your knowledge base"
echo "3. Start chatting with your documents!"
echo ""
echo "Management Commands:"
echo "- View logs: gcloud logs tail --service=$ORGANIZATION_NAME-rag-agent --region=$REGION"
echo "- Scale service: gcloud run services update $ORGANIZATION_NAME-rag-agent --max-instances=20 --region=$REGION"
echo "- Update service: ./update.sh $ORGANIZATION_NAME $PROJECT_ID"
echo ""

# Create organization-specific environment file
print_status "Creating environment configuration file..."
cat > .env.$ORGANIZATION_NAME <<EOF
# Environment configuration for $ORGANIZATION_NAME
ORGANIZATION_NAME=$ORGANIZATION_NAME
ORGANIZATION_DISPLAY_NAME=$(echo $ORGANIZATION_NAME | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION
OPENAI_API_KEY=$OPENAI_API_KEY
SERVICE_URL=$SERVICE_URL
DATA_BUCKET=$DATA_BUCKET

# Optional configurations
MAX_FILE_SIZE_MB=20
ALLOWED_FILE_TYPES=pdf,txt,md,docx,doc,rtf,html,json,csv,xml
DEBUG=false
EOF

print_success "Environment file created: .env.$ORGANIZATION_NAME"

echo ""
print_success "Deployment completed successfully! 🎉"