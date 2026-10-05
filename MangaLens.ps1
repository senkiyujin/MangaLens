$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$Main = Join-Path $ScriptDir "main.py"

if (-Not (Test-Path $Python)) {
    Write-Host "[HATA] .venv bulunamadi!"
    Write-Host "Lutfen once su komutu calistirin:"
    Write-Host ""
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -r requirements.txt"
    Write-Host ""
    Pause
    exit 1
}

Start-Process -FilePath $Python -ArgumentList $Main -NoNewWindow
