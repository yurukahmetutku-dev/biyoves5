param(
    [string]$ExecutablePath = "build/windows/dist/BiyoVes/BiyoVes.exe",
    [int]$WaitSeconds = 10
)

if (!(Test-Path $ExecutablePath)) {
    Write-Error "Test edilecek exe bulunamadı: $ExecutablePath"
    exit 1
}

Write-Host "GUI uygulaması başlatılıyor: $ExecutablePath" -ForegroundColor Cyan
$process = Start-Process -FilePath $ExecutablePath -PassThru -WindowStyle Hidden

Start-Sleep -Seconds $WaitSeconds

if ($process.HasExited) {
    if ($process.ExitCode -ne 0) {
        Write-Error "Uygulama beklenmedik şekilde kapandı. ExitCode: $($process.ExitCode)"
        exit 1
    }
    Write-Error "Uygulama belirtilen süre tamamlanmadan kapandı."
    exit 1
}

Write-Host "Uygulama çalışıyor, süreç durduruluyor..." -ForegroundColor Yellow
Stop-Process -Id $process.Id -Force

Write-Host "GUI smoke testi başarıyla tamamlandı." -ForegroundColor Green
