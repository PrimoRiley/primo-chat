@echo off
REM Multi-Organization RAG Deployment Script for Windows
REM Usage: deploy.bat <organization_name> <project_id> <openai_api_key> [region]

setlocal enabledelayedexpansion

if "%~3"=="" (
    echo Usage: %0 ^<organization_name^> ^<project_id^> ^<openai_api_key^> [region]
    echo Example: %0 acme-corp my-gcp-project-123 sk-your-api-key us-central1
    exit /b 1
)

set ORGANIZATION_NAME=%1
set PROJECT_ID=%2
set OPENAI_API_KEY=%3
set REGION=%4
if "%REGION%"=="" set REGION=us-central1

echo [INFO] Starting deployment for organization: %ORGANIZATION_NAME%
echo [INFO] Project ID: %PROJECT_ID%
echo [INFO] Region: %REGION%

REM Check required tools
echo [INFO] Checking required tools...

where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Google Cloud SDK (gcloud) is not installed
    exit /b 1
)

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed
    exit /b 1
)

where terraform >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Terraform is not installed
    exit /b 1
)

echo [SUCCESS] All required tools are available

REM Set the GCP project
echo [INFO] Setting GCP project...
gcloud config set project %PROJECT_ID%

REM Enable required APIs
echo [INFO] Enabling required Google Cloud APIs...
gcloud services enable run.googleapis.com secretmanager.googleapis.com storage.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com

echo [SUCCESS] APIs enabled successfully

REM Build and push Docker image
echo [INFO] Building Docker image...
set IMAGE_NAME=gcr.io/%PROJECT_ID%/%ORGANIZATION_NAME%-rag-agent:latest

docker build -t %IMAGE_NAME% .

echo [INFO] Pushing image to Google Container Registry...
docker push %IMAGE_NAME%

echo [SUCCESS] Docker image built and pushed successfully

REM Deploy infrastructure with Terraform
echo [INFO] Deploying infrastructure with Terraform...

cd terraform

REM Create terraform.tfvars if it doesn't exist
if not exist terraform.tfvars (
    echo [INFO] Creating terraform.tfvars...
    (
        echo organization_name = "%ORGANIZATION_NAME%"
        echo project_id       = "%PROJECT_ID%"
        echo openai_api_key   = "%OPENAI_API_KEY%"
        echo region           = "%REGION%"
    ) > terraform.tfvars
)

REM Initialize Terraform
echo [INFO] Initializing Terraform...
terraform init

REM Plan deployment
echo [INFO] Planning Terraform deployment...
terraform plan

REM Apply deployment
echo [INFO] Applying Terraform deployment...
terraform apply -auto-approve

REM Get outputs
for /f "tokens=*" %%i in ('terraform output -raw service_url') do set SERVICE_URL=%%i
for /f "tokens=*" %%i in ('terraform output -raw data_bucket') do set DATA_BUCKET=%%i

cd ..

echo [SUCCESS] Infrastructure deployed successfully!

REM Wait for service to be ready
echo [INFO] Waiting for Cloud Run service to be ready...
timeout /t 30 /nobreak >nul

REM Display deployment information
echo.
echo ==================================
echo [SUCCESS] DEPLOYMENT COMPLETED SUCCESSFULLY
echo ==================================
echo.
echo Organization: %ORGANIZATION_NAME%
echo Project ID: %PROJECT_ID%
echo Region: %REGION%
echo.
echo Service URL: %SERVICE_URL%
echo Data Bucket: %DATA_BUCKET%
echo.
echo Next Steps:
echo 1. Visit the service URL to access your RAG assistant
echo 2. Upload documents to build your knowledge base
echo 3. Start chatting with your documents!
echo.
echo Management Commands:
echo - View logs: gcloud logs tail --service=%ORGANIZATION_NAME%-rag-agent --region=%REGION%
echo - Scale service: gcloud run services update %ORGANIZATION_NAME%-rag-agent --max-instances=20 --region=%REGION%
echo - Update service: scripts\update.bat %ORGANIZATION_NAME% %PROJECT_ID%
echo.

REM Create organization-specific environment file
echo [INFO] Creating environment configuration file...
(
    echo # Environment configuration for %ORGANIZATION_NAME%
    echo ORGANIZATION_NAME=%ORGANIZATION_NAME%
    echo GCP_PROJECT_ID=%PROJECT_ID%
    echo GCP_REGION=%REGION%
    echo OPENAI_API_KEY=%OPENAI_API_KEY%
    echo SERVICE_URL=%SERVICE_URL%
    echo DATA_BUCKET=%DATA_BUCKET%
    echo.
    echo # Optional configurations
    echo MAX_FILE_SIZE_MB=20
    echo ALLOWED_FILE_TYPES=pdf,txt,md,docx,doc,rtf,html,json,csv,xml
    echo DEBUG=false
) > .env.%ORGANIZATION_NAME%

echo [SUCCESS] Environment file created: .env.%ORGANIZATION_NAME%

echo.
echo [SUCCESS] Deployment completed successfully! 🎉

endlocal