# publish.ps1

# Ensure we're in the project root
$scriptPath = $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Step 1: Read version
if (!(Test-Path .\release\version.txt)) {
    Write-Error "version.txt not found. Please run build.ps1 first."
    exit 1
}
$version = Get-Content .\release\version.txt -Raw
$releaseName = "ImageConverter2WebP.Win11.x64.v$version"
$zipFile = "release\dist_nui\image_converter2webp.Win11.x64.v$version.zip"

if (!(Test-Path $zipFile)) {
    Write-Error "Zip file not found: $zipFile"
    exit 1
}

# Step 2: Create GitHub draft release
Write-Host "Creating draft release on GitHub..."
$ghReleaseTag = "v$version"
$releaseTitle = $releaseName
$releaseBody = "Changes:`n`n- Bullet 1`n- Bullet 2`n"

# Delete existing tag/release if needed
$existing = gh release view $ghReleaseTag 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Existing release found. Deleting..."
    gh release delete $ghReleaseTag --yes
}

gh release create $ghReleaseTag `
  --title "$releaseTitle" `
  --notes "$releaseBody" `
  --draft `
  "$zipFile"

Write-Host "Draft release created: $releaseTitle"