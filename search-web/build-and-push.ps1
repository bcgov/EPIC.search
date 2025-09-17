# Docker Build and Push Script with Auto-Versioning
# This script builds a Docker image with a date-based tag and pushes it to ACR

param(
    [string]$EnvFile = "deploy.env",
    [string]$TargetEnv = "test"
)

# Function to load environment variables from .env file
function Load-EnvFile {
    param(
        [string]$FilePath
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "Environment file '$FilePath' not found!"
        Write-Host "Please create a deploy.env file with the following variables:" -ForegroundColor Yellow
        Write-Host "DOCKER_REGISTRY=your-registry.azurecr.io" -ForegroundColor Yellow
        Write-Host "DOCKER_REPOSITORY=your/repo/path" -ForegroundColor Yellow
        Write-Host "Or copy from the sample: Copy-Item deploy.env.sample deploy.env" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "Loading environment from: $FilePath" -ForegroundColor Cyan
    
    Get-Content $FilePath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            Set-Variable -Name $name -Value $value -Scope Script
            Write-Host "  Loaded: $name" -ForegroundColor Green
        }
    }
}

# Load environment variables
Load-EnvFile -FilePath $EnvFile

# Validate required environment variables
if (-not $DOCKER_REGISTRY) {
    Write-Error "DOCKER_REGISTRY not found in environment file!"
    exit 1
}

if (-not $DOCKER_REPOSITORY) {
    Write-Error "DOCKER_REPOSITORY not found in environment file!"
    exit 1
}

$Registry = $DOCKER_REGISTRY
$Repository = $DOCKER_REPOSITORY

Write-Host "Using Registry: $Registry" -ForegroundColor White
Write-Host "Using Repository: $Repository" -ForegroundColor White

# Function to get the next version number for today
function Get-NextVersionTag {
    param(
        [string]$BaseTag
    )
    
    $increment = 1
    $versionTag = "$BaseTag.$increment"
    
    # Check if image with this tag already exists by trying to pull manifest
    do {
        $tagExists = $false
        try {
            # Use docker manifest inspect to check if tag exists (suppresses output)
            $null = docker manifest inspect "$Registry/$Repository`:$versionTag" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $tagExists = $true
                $increment++
                $versionTag = "$BaseTag.$increment"
                Write-Host "Tag $BaseTag.$($increment-1) already exists, trying $versionTag..." -ForegroundColor Yellow
            }
        }
        catch {
            # Tag doesn't exist, we can use it
            $tagExists = $false
        }
    } while ($tagExists)
    
    return $versionTag
}

# Generate date tag (YYMMDD format)
$dateTag = Get-Date -Format "yyMMdd"
Write-Host "Generated base date tag: $dateTag" -ForegroundColor Cyan

# Get the next available version tag
$versionTag = Get-NextVersionTag -BaseTag $dateTag
Write-Host "Using version tag: $versionTag" -ForegroundColor Green

# Build the full image names
$versionedImage = "$Registry/$Repository`:$versionTag"
$latestImage = "$Registry/$Repository`:latest"

Write-Host "`nBuilding Docker image for environment: $TargetEnv" -ForegroundColor Cyan
Write-Host "Image tag: $versionedImage" -ForegroundColor White

# Build the Docker image with target environment
docker build --build-arg TARGET_ENV=$TargetEnv -t $versionedImage .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed!"
    exit 1
}

Write-Host "`nBuild completed successfully!" -ForegroundColor Green

# Tag the image as latest
Write-Host "`nTagging image as latest..." -ForegroundColor Cyan
docker tag $versionedImage $latestImage

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to tag image as latest!"
    exit 1
}

# Push the versioned image
Write-Host "`nPushing versioned image: $versionedImage" -ForegroundColor Cyan
docker push $versionedImage

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to push versioned image!"
    exit 1
}

# Push the latest image
Write-Host "`nPushing latest image: $latestImage" -ForegroundColor Cyan
docker push $latestImage

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to push latest image!"
    exit 1
}

Write-Host "`n✅ Successfully built and pushed:" -ForegroundColor Green
Write-Host "   📦 $versionedImage" -ForegroundColor White
Write-Host "   📦 $latestImage" -ForegroundColor White
Write-Host "`n🚀 Your pipeline should now be triggered!" -ForegroundColor Magenta