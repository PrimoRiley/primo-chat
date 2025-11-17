# Terraform Infrastructure for Multi-Tenant RAG System

This directory contains Terraform configuration for deploying organization-specific RAG agents to Google Cloud Platform.

## Prerequisites

1. **Google Cloud SDK**: Install and authenticate with `gcloud auth login`
2. **Terraform**: Install Terraform >= 1.0
3. **GCP Project**: Have a GCP project with billing enabled
4. **OpenAI API Key**: Get your API key from OpenAI

## Required APIs

Enable these APIs in your GCP project:

```bash
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## Deployment Steps

### 1. Configure Variables

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
organization_name = "acme-corp"
project_id       = "my-gcp-project-123"
openai_api_key   = "sk-your-openai-api-key"
region           = "us-central1"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan Deployment

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

### 5. Build and Deploy Application

First, build and push the Docker image:

```bash
# Build and tag the image
docker build -t gcr.io/PROJECT_ID/ORGANIZATION-rag-agent:latest .

# Push to Google Container Registry
docker push gcr.io/PROJECT_ID/ORGANIZATION-rag-agent:latest

# Deploy to Cloud Run
gcloud run deploy ORGANIZATION-rag-agent \
  --image gcr.io/PROJECT_ID/ORGANIZATION-rag-agent:latest \
  --region us-central1 \
  --platform managed
```

## Resources Created

This Terraform configuration creates:

- **Cloud Run Service**: Hosts the RAG application
- **Service Account**: With minimal required permissions
- **Secret Manager Secret**: Stores OpenAI API key securely
- **GCS Bucket**: Stores SQLite database and persistent data
- **IAM Bindings**: Proper access controls
- **Cloud Build Trigger**: (Optional) Automatic deployments

## Configuration Options

### Resource Limits

```hcl
cpu_limit = "2"          # CPU cores
memory_limit = "2Gi"     # Memory limit
max_instances = 10       # Maximum instances
min_instances = 0        # Minimum instances (0 for pay-per-use)
```

### Access Control

```hcl
enable_public_access = true  # Allow public access
```

Set to `false` for internal-only access.

### Regional Deployment

```hcl
region = "us-central1"  # GCP region
```

Choose a region close to your users.

## Multi-Organization Deployment

To deploy for multiple organizations:

### Option 1: Separate State Files

```bash
# Organization 1
terraform workspace new org1
terraform apply -var="organization_name=org1" -var="openai_api_key=sk-org1-key"

# Organization 2
terraform workspace new org2
terraform apply -var="organization_name=org2" -var="openai_api_key=sk-org2-key"
```

### Option 2: Separate Directories

```bash
# Create organization-specific directories
mkdir -p organizations/acme-corp
mkdir -p organizations/beta-corp

# Copy terraform files to each directory
cp -r terraform/* organizations/acme-corp/
cp -r terraform/* organizations/beta-corp/

# Deploy each organization separately
cd organizations/acme-corp
terraform init
terraform apply

cd ../beta-corp
terraform init
terraform apply
```

## Monitoring and Maintenance

### View Logs

```bash
gcloud logs tail --service=ORGANIZATION-rag-agent --region=us-central1
```

### Update Configuration

After changing `terraform.tfvars`:

```bash
terraform plan
terraform apply
```

### Scale Resources

Update variables and apply:

```bash
terraform apply -var="max_instances=20"
```

## Security Considerations

1. **API Keys**: Stored securely in Secret Manager
2. **Service Account**: Minimal required permissions
3. **Network**: Cloud Run provides HTTPS by default
4. **Data**: SQLite files stored in private GCS bucket

## Cost Optimization

1. **Min Instances**: Set to 0 for pay-per-use
2. **CPU/Memory**: Right-size based on usage
3. **Region**: Choose cost-effective regions
4. **Storage**: Use lifecycle rules for old data

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure all APIs are enabled
2. **Image Not Found**: Build and push Docker image first
3. **Secret Access**: Check IAM bindings for service account
4. **Database Issues**: Verify GCS bucket permissions

### Debug Commands

```bash
# Check service status
gcloud run services describe ORGANIZATION-rag-agent --region=us-central1

# View recent logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Test secret access
gcloud secrets versions access latest --secret=ORGANIZATION-openai-key
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all data including SQLite databases!

## Advanced Configuration

### Custom Domains

Add a custom domain after deployment:

```bash
gcloud run domain-mappings create --service=ORGANIZATION-rag-agent --domain=chat.yourdomain.com --region=us-central1
```

### VPC Connector

For private network access, add VPC connector configuration to `main.tf`.

### Load Balancer

For advanced routing, configure a Global Load Balancer in front of Cloud Run.