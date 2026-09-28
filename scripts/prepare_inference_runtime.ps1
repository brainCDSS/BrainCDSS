param(
    [string]$ModelRepository = "C:\finall_cdss\.tmp_model_review"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$outputDirectory = Join-Path $repositoryRoot "inference\runtime-wheels"
$projectFile = Join-Path $ModelRepository "pyproject.toml"

if (-not (Test-Path -LiteralPath $projectFile)) {
    throw "Model repository pyproject.toml not found: $projectFile"
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
Get-ChildItem -LiteralPath $outputDirectory -Filter "brainon_ai-*.whl" | Remove-Item -Force

python -m pip wheel --no-deps --wheel-dir $outputDirectory $ModelRepository
if ($LASTEXITCODE -ne 0) {
    throw "Failed to build the brainon_ai runtime wheel."
}

$wheel = Get-ChildItem -LiteralPath $outputDirectory -Filter "brainon_ai-*.whl" |
    Select-Object -First 1
if ($null -eq $wheel) {
    throw "brainon_ai wheel was not created."
}

Write-Host "Prepared runtime wheel: $($wheel.FullName)"
