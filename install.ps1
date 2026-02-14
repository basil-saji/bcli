# Configuration
$repoUrl = "https://github.com/basil-saji/bcli.git"
$installDir = "$HOME\.bcli"

Write-Host "Installing bcli..." -ForegroundColor Cyan

# 1. Clone repository
if (Test-Path $installDir) {
    Write-Host "Directory exists. Updating..."
    Set-Location $installDir
    git pull
} else {
    git clone $repoUrl $installDir
    Set-Location $installDir
}

# 2. Setup Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create a launcher script in the PATH
$launcherFolder = "$HOME\AppData\Local\Microsoft\WindowsApps"
$launcherPath = "$launcherFolder\bcli.bat"
"@echo off`ncd /d $installDir`n$installDir\venv\Scripts\python.exe $installDir\main.py %*" | Out-File -FilePath $launcherPath -Encoding ascii

Write-Host "Successfully installed! Restart your terminal and type 'bcli' to start." -ForegroundColor Green