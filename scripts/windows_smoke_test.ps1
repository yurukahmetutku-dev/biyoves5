param(
    [string]$ExecutablePath = "build/windows/dist/BiyoVes/BiyoVes.exe",
    [int]$WaitSeconds = 10,
    [int]$WindowCheckSeconds = 5
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
    } else {
        Write-Error "Uygulama belirtilen süre tamamlanmadan kapandı."
    }
    exit 1
}

$windowFound = $false
for ($i = 0; $i -lt $WindowCheckSeconds; $i++) {
    $refreshed = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if ($refreshed -and $refreshed.MainWindowHandle -ne 0) {
        $windowFound = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $windowFound) {
    Write-Error "Uygulama çalışıyor ancak pencere oluşturmadı (MainWindowHandle=0)."
    Stop-Process -Id $process.Id -Force
    exit 1
}

Write-Host "Uygulama çalışıyor, pencere tespit edildi. Süreç sonlandırılıyor..." -ForegroundColor Yellow
Stop-Process -Id $process.Id -Force

Write-Host "GUI smoke testi başarıyla tamamlandı." -ForegroundColor Green
