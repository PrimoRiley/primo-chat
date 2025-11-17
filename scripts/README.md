# Multi-Organization RAG Deployment Scripts

This directory contains deployment and management scripts for the multi-tenant RAG system.

## Prerequisites

Before running these scripts, ensure you have:

1. **Google Cloud SDK**: Installed and authenticated
2. **Docker**: Installed and running
3. **Terraform**: Installed (version >= 1.0)
4. **OpenAI API Key**: From your OpenAI account

## Quick Start

### Linux/macOS

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Deploy for organization "acme-corp"
./scripts/deploy.sh acme-corp my-gcp-project-123 sk-your-openai-key us-central1
```

### Windows

```cmd
# Deploy for organization "acme-corp"
scripts\deploy.bat acme-corp my-gcp-project-123 sk-your-openai-key us-central1
```

## Available Scripts

### 1. `deploy.sh` / `deploy.bat`

**Purpose**: Complete deployment of a new organization's RAG system

**Usage**:
```bash
./scripts/deploy.sh <organization_name> <project_id> <openai_api_key> [region]
```

**What it does**:
- Validates prerequisites and tools
- Enables required GCP APIs
- Builds and pushes Docker image
- Deploys infrastructure with Terraform
- Creates environment configuration file
- Tests the deployment

**Example**:
```bash
./scripts/deploy.sh acme-corp my-project-123 sk-1234567890 us-central1
```

### 2. `update.sh` / `update.bat`

**Purpose**: Update an existing deployment with new code

**Usage**:
```bash
./scripts/update.sh <organization_name> <project_id> [image_tag]
```

**What it does**:
- Builds new Docker image
- Pushes to Container Registry
- Updates Cloud Run service

**Example**:
```bash
./scripts/update.sh acme-corp my-project-123 v2.0
```

### 3. `cleanup.sh` / `cleanup.bat`

**Purpose**: Clean up resources for an organization

**Usage**:
```bash
./scripts/cleanup.sh <organization_name> <project_id>
```

**What it does**:
- Destroys Terraform-managed resources
- Removes Docker images
- Cleans up local files

**Example**:
```bash
./scripts/cleanup.sh acme-corp my-project-123
```

## Multi-Organization Deployment

### Deploy Multiple Organizations

```bash
# Organization 1
./scripts/deploy.sh org1 my-project-123 sk-org1-key us-central1

# Organization 2  
./scripts/deploy.sh org2 my-project-123 sk-org2-key us-west1

# Organization 3
./scripts/deploy.sh org3 my-project-123 sk-org3-key europe-west1
```

### Manage Multiple Organizations

Each deployment creates:
- Isolated Cloud Run service: `{org}-rag-agent`
- Separate data bucket: `{org}-rag-data`
- Individual secret: `{org}-openai-key`
- Environment file: `.env.{org}`

## Environment Files

After deployment, an environment file is created for each organization:

**.env.acme-corp**:
```bash
ORGANIZATION_NAME=acme-corp
GCP_PROJECT_ID=my-project-123
GCP_REGION=us-central1
OPENAI_API_KEY=sk-your-key
SERVICE_URL=https://acme-corp-rag-agent-xxx.run.app
DATA_BUCKET=acme-corp-rag-data
```

Use these files for local development:
```bash
# Load environment for specific organization
source .env.acme-corp
chainlit run app.py
```

## Configuration Options

### Resource Scaling

Edit `terraform/terraform.tfvars`:
```hcl
max_instances = 20     # Scale up for high traffic
min_instances = 1      # Keep warm instances
cpu_limit = "4"        # More CPU for processing
memory_limit = "4Gi"   # More memory for large documents
```

Apply changes:
```bash
cd terraform
terraform apply
```

### Access Control

For private access only:
```hcl
enable_public_access = false
```

Then configure IAM or VPC for authorized access.

### Regional Deployment

Deploy in different regions for better performance:
```bash
./scripts/deploy.sh eu-org my-project sk-key europe-west1
./scripts/deploy.sh asia-org my-project sk-key asia-southeast1
```

## Monitoring Commands

### View Logs
```bash
# Real-time logs
gcloud logs tail --service=acme-corp-rag-agent --region=us-central1

# Historical logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=acme-corp-rag-agent" --limit=100
```

### Service Status
```bash
# Check service details
gcloud run services describe acme-corp-rag-agent --region=us-central1

# List all deployments
gcloud run services list --filter="metadata.name~rag-agent"
```

### Resource Usage
```bash
# View metrics
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. **Docker Build Fails**
   ```bash
   docker system prune -a  # Clean up space
   docker build --no-cache -t test .
   ```

3. **Terraform State Lock**
   ```bash
   cd terraform
   terraform force-unlock <lock-id>
   ```

4. **Service Not Responding**
   ```bash
   # Check service logs
   gcloud logs tail --service=org-rag-agent --region=us-central1
   
   # Restart service
   gcloud run services update org-rag-agent --region=us-central1
   ```

### Debug Mode

Enable debug mode by setting:
```bash
export DEBUG=true
./scripts/deploy.sh org project key
```

Or edit the environment file:
```bash
echo "DEBUG=true" >> .env.org
```

## Security Best Practices

1. **API Keys**: Never commit API keys to version control
2. **Service Accounts**: Use least-privilege principle
3. **Network**: Consider VPC for sensitive data
4. **Secrets**: Rotate OpenAI API keys regularly

## Cost Optimization

1. **Auto-scaling**: Set min_instances=0 for pay-per-use
2. **Resource Limits**: Right-size CPU/memory based on usage
3. **Regional Deployment**: Choose cost-effective regions
4. **Data Lifecycle**: Implement bucket lifecycle rules

## Backup and Recovery

### Backup SQLite Data
```bash
# Download current database
gsutil cp gs://org-rag-data/org.db ./backup-org.db

# List all backups
gsutil ls gs://org-rag-data/**
```

### Restore from Backup
```bash
# Upload backup to storage
gsutil cp backup-org.db gs://org-rag-data/org.db

# Restart service to reload data
gcloud run services update org-rag-agent --region=us-central1
```

## Advanced Usage

### Custom Domains
```bash
# Map custom domain after deployment
gcloud run domain-mappings create \
  --service=org-rag-agent \
  --domain=chat.yourdomain.com \
  --region=us-central1
```

### CI/CD Integration

Add to your GitHub Actions:
```yaml
- name: Deploy RAG Service
  run: |
    ./scripts/deploy.sh ${{ secrets.ORG_NAME }} ${{ secrets.GCP_PROJECT }} ${{ secrets.OPENAI_KEY }}
```

### Load Testing
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test deployment
hey -n 1000 -c 10 https://org-rag-agent-xxx.run.app
```