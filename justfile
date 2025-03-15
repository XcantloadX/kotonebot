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
    {{venv}} python tools/make_resources.py

# Build the project using pyinstaller
build: env
    {{venv}} pyinstaller -y kotonebot-gr.spec

generate-metadata: env
    #!{{shebang_python}}
    # 更新日志
    from pathlib import Path
    with open("WHATS_NEW.md", "r", encoding="utf-8") as f:
        content = f.read()
    metadata_path = Path("kotonebot/tasks/metadata.py")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(f'WHATS_NEW = """\n{content}\n"""')
    
    # 版本号
    from subprocess import check_output
    version = check_output(['git', 'describe', '--tags', '--abbrev=0']).decode().strip()
    if version.startswith('kaa-v'):
        version = version[5:]
    with open("version", "w", encoding="utf-8") as f:
        f.write(version)

@package-resource:
    Write-Host "Packaging kotonebot-resource..."
    @{{venv}} python -m build -s kotonebot-resource

# Package KAA
@package: package-resource generate-metadata 
    {{venv}} python tools/make_resources.py -p # Make R.py in production mode

    Write-Host "Removing old build files..."
    if (Test-Path dist) { rm -r -fo dist }
    if (Test-Path build) { rm -r -fo build }
    Write-Host "Packaging KAA..."
    @{{venv}} python -m build
    
    Write-Host "Copying kotonebot-resource to dist..."
    Copy-Item .\kotonebot-resource\dist\* .\dist\

    {{venv}} python tools/make_resources.py # Make R.py in development mode

# Upload to PyPI
publish: package
    # if (git diff-index --quiet HEAD) { } else { Write-Host "Error: Commit all changes before publishing"; exit 1 }
    @Write-Host "Uploading to PyPI..."
    twine upload dist/* -u __token__ -p $env:PYPI_TOKEN

# Upload to PyPI-Test
publish-test: package
    @Write-Host "Uploading to PyPI-Test..."
    twine upload --repository testpypi dist/* -u __token__ -p $env:PYPI_TEST_TOKEN

# 
build-bootstrap:
