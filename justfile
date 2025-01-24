set dotenv-load
set shell := ["powershell", "-c"]

shebang_pwsh := if os() == 'windows' {
  'powershell.exe'
} else {
  '/usr/bin/env powershell'
}
shebang_python := if os() == 'windows' {
  'python.exe'
} else {
  '/usr/bin/env python3'
}
venv := if os() == 'windows' {
  '.\.venv\Scripts\activate; '
} else {
  'source ./.venv/bin/activate && '
}

default:
    @just --list

# Check and create virtual environment
env:
    #!{{shebang_pwsh}}
    Write-Host "Creating virtual environment..."
    $IsWindows = $env:OS -match "Windows"
    
    if (Test-Path ".venv") {
        Write-Host "Virtual environment already exists"
    } else {
        python -m venv .venv
    }
    
    if ($IsWindows) {
        .\.venv\Scripts\pip install -r requirements.dev.txt
    } else {
        ./.venv/bin/pip install -r requirements.dev.txt
    }

# Build the project using pyinstaller
build: env
    {{venv}} pyinstaller -y kotonebot-gr.spec

# Generate pyproject.toml
generate-pyproject-toml version:
    #!{{shebang_python}}
    from datetime import datetime

    today = datetime.now()
    version = today.strftime("%Y.%m.%d")

    with open("pyproject.template.toml", "r", encoding="utf-8") as f:
        template = f.read()

    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(template.replace("<<<version>>>", version))

# Package KAA
@package version: env
    Write-Host "Removing old build files..."
    if (Test-Path dist) { rm -r -fo dist }
    if (Test-Path build) { rm -r -fo build }
    Write-Host "Generating pyproject.toml..."
    just generate-pyproject-toml version
    Write-Host "Packaging KAA {{version}}..."
    @{{venv}} python -m build
    Write-Host "Removing pyproject.toml..."
    @rm -fo pyproject.toml

# Upload to PyPI
publish version: (package version)
    # if (git diff-index --quiet HEAD) { } else { Write-Host "Error: Commit all changes before publishing"; exit 1 }
    @Write-Host "Uploading to PyPI..."
    twine upload dist/* -u __token__ -p $env:PYPI_TOKEN

# Upload to PyPI-Test
publish-test version: (package version)
    @Write-Host "Uploading to PyPI-Test..."
    twine upload --repository testpypi dist/* -u __token__ -p $env:PYPI_TEST_TOKEN
