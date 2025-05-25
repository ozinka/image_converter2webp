# build.ps1

# Ensure we're in the project root
$scriptPath = $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Pre-clean
Remove-Item -Recurse -Force release\build_pyi, release\dist_pyi -ErrorAction SilentlyContinue

# Step 1: Bump version and extract version string
Write-Host "Bumping version..."
$bumpOutput = python .\bump_version.py
if ($bumpOutput -match "Bumped version to:\s*(\d+\.\d+\.\d+)") {
    $version = $Matches[1]
} else {
    Write-Error "Could not parse version string."
    exit 1
}
Write-Host "New version: $version"

# Step 2: Build with PyInstaller
Write-Host "Building with PyInstaller..."
pyinstaller image_converter2webp.spec `
  --distpath release\dist_pyi `
  --workpath release\build_pyi

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

# Step 3: Create versioned zip file
$releaseName = "ImageConverter2WebP.Win11.x64.v$version"
$zipFile = "release\dist_pyi\image_converter2webp.Win11.x64.v$version.zip"
$distFolder = "release\dist_pyi\image_converter2webp"

if (Test-Path $zipFile) {
    Remove-Item $zipFile
}
Compress-Archive -Path "$distFolder\*" -DestinationPath $zipFile
Write-Host "Zip created: $zipFile"

# Step 4: Output version to file for publish script
$version | Out-File -Encoding ascii -NoNewline .\release\version.txt
