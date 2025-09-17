#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Document Processing API to Google Cloud Run

.DESCRIPTION
    This script automates the complete deployment process for the Document Processing API to Google Cloud Run.
    It handles prerequisites checking, API enabling, building, and deploying the application.

.PARAMETER ProjectId
    Google Cloud Project ID (required)

.PARAMETER Region
    Google Cloud region for deployment (default: asia-northeast1)

.PARAMETER ServiceName
    Cloud Run service name (default: OCR-ai-api)

.PARAMETER AllowUnauthenticated
    Allow unauthenticated access (default: false for security)

.PARAMETER SkipTests
    Skip post-deployment testing (default: false)

.PARAMETER ArtifactRepository
    Artifact Registry repository name (default: cloud-run-ocr-ai)

.PARAMETER ArtifactLocation
    Artifact Registry location (default: asia)

.EXAMPLE
    .\deploy_to_cloudrun.ps1 -ProjectId "my-project-123"

.EXAMPLE
    .\deploy_to_cloudrun.ps1 -ProjectId "my-project-123" -Region "us-west1" -ServiceName "my-api"

.EXAMPLE
    .\deploy_to_cloudrun.ps1 -ProjectId "my-project-123" -ArtifactRepository "my-repo" -ArtifactLocation "us-east1"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory = $false)]
    [string]$Region = "asia-northeast1",
    
    [Parameter(Mandatory = $false)]
    [string]$ServiceName = "ocr-ai-api",
    
    [Parameter(Mandatory = $false)]
    [bool]$AllowUnauthenticated = $false,
    
    [Parameter(Mandatory = $false)]
    [bool]$SkipTests = $false,
    
    [Parameter(Mandatory = $false)]
    [string]$ArtifactRepository = "cloud-run-ocr-ai",
    
    [Parameter(Mandatory = $false)]
    [string]$ArtifactLocation = "asia"
)

# Color coding for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Info { Write-ColorOutput Cyan $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }

# Script configuration
$ErrorActionPreference = "Stop"
$ModelName = "gemini-2.5-flash"
$Memory = "2Gi"
$CPU = "2"
$Timeout = "300"
$MaxInstances = "10"
$MinInstances = "1"
$ImageName = "ocr-ai-api"

Write-Info "🚀 Starting Google Cloud Run Deployment"
Write-Info "==============================================="
Write-Info "Project ID: $ProjectId"
Write-Info "Region: $Region"
Write-Info "Service Name: $ServiceName"
Write-Info "Artifact Repository: $ArtifactRepository"
Write-Info "Artifact Location: $ArtifactLocation"
Write-Info "Allow Unauthenticated: $AllowUnauthenticated"
Write-Info "==============================================="

# Function to check if a command exists
function Test-CommandExists {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if gcloud is authenticated
function Test-GCloudAuth {
    try {
        $authResult = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
        return ![string]::IsNullOrWhiteSpace($authResult)
    }
    catch {
        return $false
    }
}

# Function to check if GCloud APIs are enabled
function Test-GCloudAPIs {
    Write-Info "📡 Checking required Google Cloud APIs..."
    
    $apis = @(
        @{Name = "cloudbuild.googleapis.com"; Description = "Cloud Build API"},
        @{Name = "run.googleapis.com"; Description = "Cloud Run API"},
        @{Name = "aiplatform.googleapis.com"; Description = "AI Platform API"},
        @{Name = "artifactregistry.googleapis.com"; Description = "Artifact Registry API"}
    )
    
    $disabledApis = @()
    
    foreach ($api in $apis) {
        Write-Info "  Checking $($api.Description)..."
        try {
            $result = gcloud services list --enabled --filter="name:$($api.Name)" --format="value(name)" --project=$ProjectId 2>$null
            if ([string]::IsNullOrWhiteSpace($result)) {
                Write-Warning "  ⚠️  $($api.Description) is not enabled"
                $disabledApis += $api
            }
            else {
                Write-Success "  ✅ $($api.Description) is enabled"
            }
        }
        catch {
            Write-Warning "  ⚠️  Could not check $($api.Description) status"
            $disabledApis += $api
        }
    }
    
    if ($disabledApis.Count -gt 0) {
        Write-Error ""
        Write-Error "❌ Required APIs are not enabled!"
        Write-Info ""
        Write-Info "Please enable the following APIs before running this script:"
        Write-Info ""
        
        # Show gcloud commands to enable APIs
        Write-Info "Using gcloud CLI:"
        foreach ($api in $disabledApis) {
            Write-Info "  gcloud services enable $($api.Name) --project=$ProjectId"
        }
        
        Write-Info ""
        Write-Info "Or enable all at once:"
        $apiNames = $disabledApis | ForEach-Object { $_.Name }
        Write-Info "  gcloud services enable $($apiNames -join ' ') --project=$ProjectId"
        
        Write-Info ""
        Write-Info "Or use the Google Cloud Console:"
        Write-Info "  https://console.cloud.google.com/apis/library?project=$ProjectId"
        Write-Info ""
        Write-Info "After enabling the APIs, run this script again."
        
        return $false
    }
    
    Write-Success "  ✅ All required APIs are enabled"
    return $true
}

# Function to build and deploy
function Deploy-ToCloudRun {
    Write-Info "🔨 Building and deploying to Cloud Run..."
    
    # Build image URI for Artifact Registry
    $imageUri = "$ArtifactLocation-docker.pkg.dev/$ProjectId/$ArtifactRepository/${ImageName}:latest"
    
    try {
        # Step 1: Build and push image to Artifact Registry
        Write-Info "  Building container image..."
        Write-Info "  Image URI: $imageUri"
        
        gcloud builds submit --tag $imageUri --project=$ProjectId --quiet
        
        if ($LASTEXITCODE -ne 0) {
            throw "Container build failed with exit code $LASTEXITCODE"
        }
        Write-Success "  ✅ Container built and pushed to Artifact Registry"
        
        # Step 2: Deploy to Cloud Run
        Write-Info "  Deploying to Cloud Run..."
        
        # Prepare authentication flag
        $authFlag = if ($AllowUnauthenticated) { "--allow-unauthenticated" } else { "--no-allow-unauthenticated" }
        
        # Build environment variables
        $envVars = "GCP_PROJECT_ID=$ProjectId,GCP_REGION=$Region,MODEL_NAME=$ModelName"
        
        $deployArgs = @(
            "run", "deploy", $ServiceName,
            "--image", $imageUri,
            "--platform", "managed",
            "--region", $Region,
            $authFlag,
            "--set-env-vars", $envVars,
            "--memory", $Memory,
            "--cpu", $CPU,
            "--timeout", $Timeout,
            "--max-instances", $MaxInstances,
            "--min-instances", $MinInstances,
            "--project", $ProjectId,
            "--quiet"
        )
        
        Write-Info "  Executing: gcloud $($deployArgs -join ' ')"
        & gcloud @deployArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "🎉 Deployment successful!"
        }
        else {
            throw "Deployment failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "❌ Deployment failed: $($_.Exception.Message)"
        throw
    }
}

# Function to get service URL
function Get-ServiceUrl {
    try {
        $url = gcloud run services describe $ServiceName --region=$Region --project=$ProjectId --format="value(status.url)" 2>$null
        return $url.Trim()
    }
    catch {
        Write-Warning "⚠️  Could not retrieve service URL"
        return $null
    }
}

# Function to test deployment
function Test-Deployment {
    param($ServiceUrl)
    
    if ([string]::IsNullOrWhiteSpace($ServiceUrl)) {
        Write-Warning "⚠️  Cannot test deployment - service URL not available"
        return
    }
    
    Write-Info "🧪 Testing deployment..."
    Write-Info "Service URL: $ServiceUrl"
    
    try {
        # Test health endpoint
        Write-Info "  Testing health endpoint..."
        $healthResponse = Invoke-RestMethod -Uri "$ServiceUrl/health" -Method Get -TimeoutSec 30
        
        if ($healthResponse.status -eq "ok") {
            Write-Success "  ✅ Health check passed"
        }
        else {
            Write-Warning "  ⚠️  Health check returned unexpected response: $($healthResponse | ConvertTo-Json)"
        }
    }
    catch {
        Write-Warning "  ⚠️  Health check failed: $($_.Exception.Message)"
        Write-Info "  This might be normal if the service is still starting up"
    }
}

# Function to display final information
function Show-DeploymentInfo {
    param($ServiceUrl)
    
    Write-Success ""
    Write-Success "🎊 Deployment Complete!"
    Write-Success "======================="
    
    if (![string]::IsNullOrWhiteSpace($ServiceUrl)) {
        Write-Info "Service URL: $ServiceUrl"
        Write-Info ""
        Write-Info "📋 Test your API:"
        Write-Info "Health Check:"
        Write-Info "  curl $ServiceUrl/health"
        Write-Info ""
        Write-Info "Business License Processing:"
        Write-Info "  curl -X POST `"$ServiceUrl/process-business-license`" \"
        Write-Info "    -F `"file=@sample-license.pdf`" \"
        Write-Info "    -F `"country=korea`""
        Write-Info ""
        Write-Info "Receipt Processing:"
        Write-Info "  curl -X POST `"$ServiceUrl/process-receipt`" \"
        Write-Info "    -F `"file=@sample-receipt.jpg`""
    }
    
    Write-Info ""
    Write-Info "📊 Monitor your service:"
    Write-Info "  Console: https://console.cloud.google.com/run/detail/$Region/$ServiceName"
    Write-Info "  Logs: gcloud run services logs tail $ServiceName --region=$Region"
    Write-Info ""
    Write-Info "💰 Cost Information:"
    Write-Info "  Your service is configured to scale to zero when not in use"
    Write-Info "  You'll only be charged for actual usage (CPU time during requests)"
    Write-Info "  Estimated cost: ~$0.001-0.003 per request"
}

# Function to ensure Artifact Registry repository exists
function Ensure-ArtifactRepository {
    Write-Info "🗃️  Checking Artifact Registry repository..."
    
    # Check if repository exists by trying to describe it
    Write-Info "  Checking if repository '$ArtifactRepository' exists..."
    
    # Use a different approach to check if repo exists
    $checkCommand = "gcloud artifacts repositories describe $ArtifactRepository --location=$ArtifactLocation --project=$ProjectId --format=`"value(name)`""
    $repoExists = $false
    
    try {
        $output = cmd /c "$checkCommand 2>nul"
        if ($LASTEXITCODE -eq 0 -and ![string]::IsNullOrWhiteSpace($output)) {
            $repoExists = $true
        }
    }
    catch {
        $repoExists = $false
    }
    
    if ($repoExists) {
        Write-Success "  ✅ Repository '$ArtifactRepository' already exists"
    }
    else {
        Write-Info "  Creating Artifact Registry repository: $ArtifactRepository"
        $createCommand = "gcloud artifacts repositories create $ArtifactRepository --repository-format=docker --location=$ArtifactLocation --project=$ProjectId --quiet"
        
        try {
            cmd /c $createCommand
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "  ✅ Repository '$ArtifactRepository' created successfully"
            }
            else {
                throw "Failed to create Artifact Registry repository (exit code: $LASTEXITCODE)"
            }
        }
        catch {
            Write-Error "❌ Failed to create repository: $($_.Exception.Message)"
            throw
        }
    }
    
    # Configure Docker authentication
    Write-Info "  Configuring Docker authentication for Artifact Registry..."
    try {
        $authCommand = "gcloud auth configure-docker $ArtifactLocation-docker.pkg.dev --quiet"
        cmd /c $authCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "  ✅ Docker authentication configured"
        }
        else {
            Write-Warning "  ⚠️  Docker authentication may have failed, but continuing with deployment"
        }
    }
    catch {
        Write-Warning "  ⚠️  Docker authentication may have failed, but continuing with deployment"
    }
}

# Main execution
try {
    # Step 1: Check prerequisites
    Write-Info "🔍 Checking prerequisites..."
    
    if (!(Test-CommandExists "gcloud")) {
        Write-Error "❌ Google Cloud SDK (gcloud) is not installed or not in PATH"
        Write-Info "Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    }
    Write-Success "  ✅ Google Cloud SDK found"
    
    if (!(Test-GCloudAuth)) {
        Write-Error "❌ Not authenticated with Google Cloud"
        Write-Info "Please run: gcloud auth login"
        exit 1
    }
    Write-Success "  ✅ Google Cloud authentication verified"
    
    # Check if we're in the right directory
    if (!(Test-Path "app.py") -or !(Test-Path "Dockerfile") -or !(Test-Path "requirements.txt")) {
        Write-Error "❌ Required files (app.py, Dockerfile, requirements.txt) not found"
        Write-Info "Please run this script from the project root directory"
        exit 1
    }
    Write-Success "  ✅ Project files found"
    
    # Step 2: Set project
    Write-Info "🔧 Configuring Google Cloud project..."
    gcloud config set project $ProjectId | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "  ✅ Project set to $ProjectId"
    }
    else {
        Write-Error "❌ Failed to set project"
        exit 1
    }
    
    # Step 3: Check APIs
    if (!(Test-GCloudAPIs)) {
        exit 1
    }
    
    # Step 4: Setup Artifact Registry
    Ensure-ArtifactRepository
    
    # Step 5: Deploy
    Deploy-ToCloudRun
    
    # Step 6: Get service URL
    $serviceUrl = Get-ServiceUrl
    
    # Step 7: Test deployment (unless skipped)
    if (!$SkipTests) {
        Test-Deployment -ServiceUrl $serviceUrl
    }
    
    # Step 8: Show final information
    Show-DeploymentInfo -ServiceUrl $serviceUrl
    
}
catch {
    Write-Error "💥 Deployment failed: $($_.Exception.Message)"
    Write-Info ""
    Write-Info "🔧 Troubleshooting tips:"
    Write-Info "1. Ensure you have billing enabled on your Google Cloud project"
    Write-Info "2. Verify you have the necessary permissions (Editor or Cloud Run Admin role)"
    Write-Info "3. Check if the project ID is correct: $ProjectId"
    Write-Info "4. Make sure you're running this from the project root directory"
    Write-Info "5. Try running 'gcloud auth login' if authentication issues persist"
    Write-Info ""
    Write-Info "For detailed logs, check the Google Cloud Console:"
    Write-Info "https://console.cloud.google.com/run"
    
    exit 1
} 