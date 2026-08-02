[CmdletBinding()]
param(
    [string]$PythonExecutable = "",
    [string]$MakeNsisExecutable = "",
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$buildVenv = Join-Path $projectRoot ".build-venv"
$buildPython = Join-Path $buildVenv "Scripts\python.exe"
$requirements = Join-Path $projectRoot "requirements-build.txt"
$specFile = Join-Path $projectRoot "packaging\windows\JobCompass.spec"
$installerScript = Join-Path $projectRoot "packaging\windows\JobCompass.nsi"
$appVersionFile = Join-Path $projectRoot "app\__init__.py"

$versionMatch = [regex]::Match(
    (Get-Content -Raw -Encoding UTF8 $appVersionFile),
    '__version__\s*=\s*"([^"]+)"'
)
if (-not $versionMatch.Success) {
    throw "Could not read JobCompass version from app\__init__.py"
}
$appVersion = $versionMatch.Groups[1].Value

if (-not $PythonExecutable) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $PythonExecutable = $pythonCommand.Source
    } else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $launcher) {
            throw "Python 3.11 or newer was not found. Pass -PythonExecutable explicitly."
        }
        $PythonExecutable = $launcher.Source
    }
}

if (-not (Test-Path -LiteralPath $buildPython)) {
    Write-Host "Creating isolated build environment..."
    if ([System.IO.Path]::GetFileName($PythonExecutable) -ieq "py.exe") {
        & $PythonExecutable -3 -m venv $buildVenv
    } else {
        & $PythonExecutable -m venv $buildVenv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the build environment."
    }
}

Write-Host "Installing build dependencies..."
& $buildPython -m pip install --disable-pip-version-check -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "Could not install build dependencies."
}

if (-not $SkipTests) {
    Write-Host "Running tests..."
    & $buildPython -m unittest discover -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed; distribution was not built."
    }
}

$generatedDirectories = @(
    (Join-Path $projectRoot "build"),
    (Join-Path $projectRoot "dist"),
    (Join-Path $projectRoot "release"),
    (Join-Path $projectRoot ".portable-staging")
)
foreach ($directory in $generatedDirectories) {
    $fullDirectory = [System.IO.Path]::GetFullPath($directory)
    if (-not $fullDirectory.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a path outside the project: $fullDirectory"
    }
    if (Test-Path -LiteralPath $fullDirectory) {
        Remove-Item -LiteralPath $fullDirectory -Recurse -Force
    }
}

$buildDirectory = Join-Path $projectRoot "build"
$distDirectory = Join-Path $projectRoot "dist"
$releaseDirectory = Join-Path $projectRoot "release"
New-Item -ItemType Directory -Path $releaseDirectory | Out-Null

Write-Host "Building the Windows application..."
& $buildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --workpath $buildDirectory `
    --distpath $distDirectory `
    $specFile
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$applicationDirectory = Join-Path $distDirectory "JobCompass"
$applicationExecutable = Join-Path $applicationDirectory "JobCompass.exe"
if (-not (Test-Path -LiteralPath $applicationExecutable)) {
    throw "JobCompass.exe was not created."
}

Write-Host "Creating the portable ZIP..."
$portableRoot = Join-Path $projectRoot ".portable-staging\JobCompass"
New-Item -ItemType Directory -Path $portableRoot | Out-Null
Copy-Item -Path (Join-Path $applicationDirectory "*") -Destination $portableRoot -Recurse
New-Item -ItemType File -Path (Join-Path $portableRoot "portable.flag") | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $portableRoot
$portableArchive = Join-Path $releaseDirectory "JobCompass-$appVersion-Portable.zip"
Compress-Archive -Path (Join-Path $portableRoot "*") -DestinationPath $portableArchive -CompressionLevel Optimal

if (-not $SkipInstaller) {
    if (-not $MakeNsisExecutable) {
        $localCompiler = Get-ChildItem `
            -LiteralPath (Join-Path $projectRoot ".tools\nsis") `
            -Filter "makensis.exe" `
            -Recurse `
            -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
        $candidates = @(
            $localCompiler,
            (Join-Path ${env:ProgramFiles} "NSIS\makensis.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "NSIS\makensis.exe")
        )
        $MakeNsisExecutable = $candidates |
            Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
            Select-Object -First 1
    }
    if (-not $MakeNsisExecutable) {
        throw "NSIS makensis.exe was not found. Install NSIS or use -SkipInstaller."
    }
    Write-Host "Building the installer..."
    & $MakeNsisExecutable "/DAPP_VERSION=$appVersion" $installerScript
    if ($LASTEXITCODE -ne 0) {
        throw "NSIS installer build failed."
    }
}

Remove-Item -LiteralPath (Join-Path $projectRoot ".portable-staging") -Recurse -Force

$artifacts = Get-ChildItem -LiteralPath $releaseDirectory -File |
    Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
    Sort-Object Name
$checksumLines = foreach ($artifact in $artifacts) {
    $hash = (Get-FileHash -LiteralPath $artifact.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $($artifact.Name)"
}
[System.IO.File]::WriteAllLines(
    (Join-Path $releaseDirectory "SHA256SUMS.txt"),
    $checksumLines,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Build complete:"
Get-ChildItem -LiteralPath $releaseDirectory -File |
    Select-Object Name, Length, LastWriteTime
