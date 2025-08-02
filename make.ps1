#!/usr/bin/env pwsh

# Build and upload kotonebot to PyPI
# Requires PyPI token in .env file as PYPI_TOKEN

param(
    [string]$EnvFile = ".env",
    [switch]$Clean,
    [switch]$TestPyPI
)

# Function to read .env file
function Get-EnvVariables {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Error "Environment file not found: $Path"
        exit 1
    }
    
    $envVars = @{}
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*([^=]+)\s*=\s*(.*?)\s*$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove surrounding quotes if present
            if ($value -match '^["''](.*)["'']$') {
                $value = $matches[1]
            }
            $envVars[$key] = $value
        }
    }
    return $envVars
}

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    return $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Main script
Write-Host "? Starting PyPI build and upload process..." -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Error "pyproject.toml not found. Please run this script from the project root."
    exit 1
}

# Clean previous builds if requested
if ($Clean) {
    Write-Host "? Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path "dist") {
        Remove-Item -Path "dist" -Recurse -Force
    }
    if (Test-Path "build") {
        Remove-Item -Path "build" -Recurse -Force
    }
    if (Test-Path "*.egg-info") {
        Remove-Item -Path "*.egg-info" -Recurse -Force
    }
}

# Check required tools
$requiredTools = @("python", "pip")
foreach ($tool in $requiredTools) {
    if (-not (Test-Command $tool)) {
        Write-Error "Required tool not found: $tool"
        exit 1
    }
}

# Install build and twine if not already installed
Write-Host "? Checking required packages..." -ForegroundColor Cyan
pip install build twine --quiet

# Read environment variables
Write-Host "? Reading environment variables from $EnvFile..." -ForegroundColor Cyan
$envVars = Get-EnvVariables -Path $EnvFile

# Check for PyPI token
if (-not $envVars.ContainsKey("PYPI_TOKEN")) {
    Write-Error "PYPI_TOKEN not found in $EnvFile"
    Write-Host "Please add your PyPI token to $EnvFile as:"
    Write-Host "PYPI_TOKEN=your_pypi_token_here"
    exit 1
}

# Set environment variables for twine
$env:PYPI_TOKEN = $envVars["PYPI_TOKEN"]
$env:TWINE_USERNAME = "__token__"  # Required for token-based authentication

# Build the project
Write-Host "? Building project..." -ForegroundColor Cyan
try {
    python -m build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Build failed"
        exit 1
    }
    Write-Host "? Build completed successfully" -ForegroundColor Green
}
catch {
    Write-Error "Build failed: $_"
    exit 1
}

# Check if dist files were created
$distFiles = Get-ChildItem -Path "dist" -File
if ($distFiles.Count -eq 0) {
    Write-Error "No distribution files found in dist/ directory"
    exit 1
}

Write-Host "? Built files:" -ForegroundColor Cyan
$distFiles | ForEach-Object {
    Write-Host "  - $($_.Name)"
}

# Upload to PyPI
$repository = if ($TestPyPI) { "--repository testpypi" } else { "" }
$repositoryName = if ($TestPyPI) { "TestPyPI" } else { "PyPI" }

Write-Host "? Uploading to $repositoryName..." -ForegroundColor Cyan
try {
    if ($TestPyPI) {
        twine upload --repository testpypi dist/* -u __token__ -p $env:PYPI_TOKEN
    } else {
        twine upload dist/* -u __token__ -p $env:PYPI_TOKEN
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Upload failed"
        exit 1
    }
    
    Write-Host "? Successfully uploaded to $repositoryName!" -ForegroundColor Green
}
catch {
    Write-Error "Upload failed: $_"
    exit 1
}

# Clean up environment variables
Remove-Item Env:PYPI_TOKEN
Remove-Item Env:TWINE_USERNAME

Write-Host "? All done!" -ForegroundColor Green