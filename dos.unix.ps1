# dos.unix.ps1
# Usage: .\dos.unix.ps1 "C:\path\to\project"

param (
    [string]$TargetDir = "."
)

# Determine dos2unix path
$dos2unixPath = Join-Path -Path (Get-Location) -ChildPath "dos2unix.exe"
if (-Not (Test-Path $dos2unixPath)) {
    Write-Host "❌ dos2unix.exe not found in current directory" -ForegroundColor Red
    exit 1
}

Write-Host "🔍 Scanning directory: $TargetDir" -ForegroundColor Cyan

Get-ChildItem -Path $TargetDir -Recurse -File | ForEach-Object {
    try {
        & $dos2unixPath $_.FullName
        Write-Host "✅ Converted: $($_.FullName)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Skipped: $($_.FullName)" -ForegroundColor Yellow
    }
}

Write-Host "✅ All files processed." -ForegroundColor Green
