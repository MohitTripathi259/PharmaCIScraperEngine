# PowerShell script to test Change Analysis module
# Run this script to verify the installation and test the API

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Change Analysis Module - Test Script" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Note: If you have a .venv311 virtual environment, activate it first:
# .\.venv311\Scripts\Activate.ps1

# 1) Upgrade pip and install project
Write-Host "Step 1: Upgrading pip and installing project in editable mode..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Pip upgraded successfully" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to upgrade pip" -ForegroundColor Red
    exit 1
}

pip install -e . --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Project installed in editable mode" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to install project" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2) Run tests
Write-Host "Step 2: Running unit tests..." -ForegroundColor Yellow
python -m pytest -q tests/unit/test_change_analysis.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] All tests passed!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Some tests failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3) Run demo
Write-Host "Step 3: Running demo script..." -ForegroundColor Yellow
python demo.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Demo completed successfully" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Demo failed" -ForegroundColor Red
}
Write-Host ""

# 4) Test API
Write-Host "Step 4: Testing API server..." -ForegroundColor Yellow
Write-Host "Starting API server on port 8080..." -ForegroundColor Cyan

# Start API server in background
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python -m uvicorn src.api.main:app --port 8080
}

# Wait for server to start
Write-Host "Waiting for server to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Check if server is running
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -TimeoutSec 5
    Write-Host "[OK] API server is running" -ForegroundColor Green
    Write-Host "Health check response: $($health | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] API server is not responding" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Stop-Job -Job $apiJob
    Remove-Job -Job $apiJob
    exit 1
}
Write-Host ""

# 5) Test analyze endpoint
Write-Host "Step 5: Testing /v1/changes/analyze endpoint..." -ForegroundColor Yellow

$payload = @{
    prev_dom = "<html><body><h1>Trial 3</h1></body></html>"
    cur_dom  = "<html><body><h1>Trial 4</h1></body></html>"
    prev_ss  = ""
    cur_ss   = ""
    goal     = "Track new trials and approvals"
    domain   = "regulatory"
    url      = "https://example.com"
    keywords = @("trial", "phase", "approval", "fda")
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Method POST `
        -Uri "http://localhost:8080/v1/changes/analyze" `
        -ContentType "application/json" `
        -Body $payload `
        -TimeoutSec 10

    Write-Host "[OK] API endpoint test successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    Write-Host "  Change Detected:   $($result.has_change)" -ForegroundColor White
    Write-Host "  Text Added:        $($result.text_added)" -ForegroundColor White
    Write-Host "  Text Removed:      $($result.text_removed)" -ForegroundColor White
    Write-Host "  Similarity:        $($result.similarity * 100)%" -ForegroundColor White
    Write-Host "  Importance:        $($result.importance.ToUpper())" -ForegroundColor White
    Write-Host "  Import Score:      $($result.import_score)/10" -ForegroundColor White
    Write-Host "  Alert Level:       $($result.alert_criteria.ToUpper())" -ForegroundColor White
    Write-Host "  Summary:           $($result.summary_change)" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "[ERROR] API request failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Stop-Job -Job $apiJob
    Remove-Job -Job $apiJob
    exit 1
}

# 6) Cleanup
Write-Host "Step 6: Cleaning up..." -ForegroundColor Yellow
Stop-Job -Job $apiJob
Remove-Job -Job $apiJob
Write-Host "[OK] API server stopped" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. To start the API server manually:" -ForegroundColor White
Write-Host "     python -m uvicorn src.api.main:app --reload --port 8080" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. View API documentation:" -ForegroundColor White
Write-Host "     http://localhost:8080/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Run demo script:" -ForegroundColor White
Write-Host "     python demo.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Import in your code:" -ForegroundColor White
Write-Host "     from change_analysis import analyze_change" -ForegroundColor Gray
Write-Host ""
