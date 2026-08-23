# Build the buyer folder. Run from host\:  powershell -File pack_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing PyInstaller..."
py -3 -m pip install -q -r requirements.txt pyinstaller

Write-Host "Building Desk154.exe..."
py -3 -m PyInstaller --noconfirm desk154.spec

$src = Join-Path $PSScriptRoot "dist\Desk154"
$out = Join-Path $PSScriptRoot "dist\Desk154-Windows"
if (-not (Test-Path $src)) { throw "dist\Desk154 missing" }

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item $out -ItemType Directory | Out-Null
Copy-Item -Path (Join-Path $src "*") -Destination $out -Recurse

$guide = Get-ChildItem (Join-Path $PSScriptRoot "packaging") -Filter "*.txt" | Select-Object -First 1
if ($guide) {
    Copy-Item $guide.FullName (Join-Path $out $guide.Name)
    Copy-Item $guide.FullName (Join-Path $out "readme.txt")
}

$zip = Join-Path $PSScriptRoot "dist\Desk154-Windows.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $out -DestinationPath $zip -Force

Write-Host "OK"
Write-Host "Folder: $out"
Write-Host "Zip:    $zip"
Write-Host "Give customer the zip + flashed puck + data USB cable."
