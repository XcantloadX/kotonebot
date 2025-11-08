set dotenv-load
set windows-shell := ["powershell", "-c"]
set shell := ["pwsh", "-c"]

shebang_pwsh := if os() == 'windows' {
  'powershell.exe'
} else {
  '/usr/bin/env pwsh'
}
shebang_python := if os() == 'windows' {
  'python.exe'
} else {
  '/usr/bin/env python'
}

default:
    @just --list

fetch-submodule:
    git submodule update --init --remote --recursive

resource:
    python tools\make_resources.py

devtool:
    cd kotonebot-devtool; npm run dev

# Check and create virtual environment using uv
env: fetch-submodule
    #!{{shebang_pwsh}}
    Write-Host "Installing requirements with uv..."
    $IsWindows = $env:OS -match "Windows"
    
    if ($IsWindows) {
        uv sync --extra dev --extra windows
    } else {
        uv sync --extra dev
    }

# Install all optional dependencies
env-all: fetch-submodule
    #!{{shebang_pwsh}}
    Write-Host "Installing all dependencies with uv..."
    uv sync --all-extras

# Install with uv and sync with pyproject.toml
sync:
    #!{{shebang_pwsh}}
    Write-Host "Syncing project with uv..."
    uv sync

# Run tests with uv
test:
    #!{{shebang_pwsh}}
    Write-Host "Running tests with uv..."
    uv run python -m unittest discover

# Check code with uv
check:
    #!{{shebang_pwsh}}
    Write-Host "Running code checks..."
    uv run ruff check .
    uv run black --check .

@package-resource:
    Write-Host "Packaging kotonebot-resource..."
    @python -m build -s kotonebot-resource

# Upload to PyPI
publish:
    # if (git diff-index --quiet HEAD) { } else { Write-Host "Error: Commit all changes before publishing"; exit 1 }
    @Write-Host "Uploading to PyPI..."
    twine upload dist/* -u __token__ -p $env:PYPI_TOKEN

# Upload to PyPI-Test
publish-test:
    @Write-Host "Uploading to PyPI-Test..."
    twine upload --repository testpypi dist/* -u __token__ -p $env:PYPI_TEST_TOKEN
