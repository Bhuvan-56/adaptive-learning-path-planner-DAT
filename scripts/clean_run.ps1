[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Sha,

    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
    try {
        $RepoUrl = (git config --get remote.origin.url).Trim()
    } catch {
        $RepoUrl = "https://github.com/Bhuvan-56/adaptive-learning-path-planner-DAT.git"
    }
}

if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
    Write-Host "FAIL: RepoUrl could not be determined."
    exit 1
}

$tempBase = [System.IO.Path]::GetTempPath()
$runId = [System.Guid]::NewGuid().ToString("N").Substring(0, 8)
$cloneDir = Join-Path $tempBase "dat11_clean_$runId"

Write-Host "=========================================================="
Write-Host "CLEAN RUN AUDIT SCRIPT"
Write-Host "Repo URL: $RepoUrl"
Write-Host "Target SHA: $Sha"
Write-Host "Clone Dir: $cloneDir"
Write-Host "=========================================================="

try {
    # 1. Clone into temporary directory
    Write-Host "[1/6] Cloning repository..."
    New-Item -ItemType Directory -Path $cloneDir -Force | Out-Null
    & git clone $RepoUrl $cloneDir
    if ($LASTEXITCODE -ne 0) {
        throw "git clone failed with exit code $LASTEXITCODE"
    }

    # 2. Checkout specified SHA
    Write-Host "[2/6] Checking out SHA $Sha..."
    Push-Location $cloneDir
    & git checkout $Sha
    if ($LASTEXITCODE -ne 0) {
        throw "git checkout $Sha failed with exit code $LASTEXITCODE"
    }

    # 3. Create virtual environment
    Write-Host "[3/6] Creating clean virtual environment..."
    $pythonBase = ""
    if ($env:PYTHON_EXE -and (Test-Path $env:PYTHON_EXE)) {
        $pythonBase = $env:PYTHON_EXE
    } elseif (Test-Path "C:\Users\5520\AppData\Local\Programs\Python\Python311\python.exe") {
        $pythonBase = "C:\Users\5520\AppData\Local\Programs\Python\Python311\python.exe"
    } elseif (Test-Path "C:\Users\bhuva\anaconda3\python.exe") {
        $pythonBase = "C:\Users\bhuva\anaconda3\python.exe"
    } else {
        $pythonBase = (Get-Command python -ErrorAction SilentlyContinue).Source
    }

    if ([string]::IsNullOrWhiteSpace($pythonBase)) {
        throw "Could not locate a suitable base Python executable."
    }

    Write-Host "Using base Python: $pythonBase"
    $venvDir = Join-Path $cloneDir ".venv_clean"
    & $pythonBase -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "venv creation failed with exit code $LASTEXITCODE"
    }

    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "Venv python not found at $venvPython"
    }

    # 4. Install dependencies
    Write-Host "[4/6] Installing dependencies from requirements.txt..."
    & $venvPython -m pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE"
    }

    # 5. Run full pytest suite
    Write-Host "[5/6] Running pytest test suite..."
    & $venvPython -m pytest -q -rs
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest test suite failed with exit code $LASTEXITCODE"
    }

    # 6. Run demo CLI command
    Write-Host "[6/8] Running end-to-end demo command..."
    $demoOut = Join-Path $cloneDir "evaluation\results\w3\demo"
    & $venvPython -m src.cli demo --out $demoOut --seed 20261012 --budget 10
    if ($LASTEXITCODE -ne 0) {
        throw "Demo command failed with exit code $LASTEXITCODE"
    }

    # Verify expected output artifacts
    $expectedFiles = @(
        "manifest.json",
        "plan_novice_day1.json",
        "trace_novice_day1.json",
        "plan_intermediate_day1.json",
        "trace_intermediate_day1.json",
        "plan_assessment_passed.json",
        "trace_assessment_passed.json",
        "plan_assessment_failed.json",
        "trace_assessment_failed.json",
        "plan_missed_day.json",
        "trace_missed_day.json",
        "plan_reduced_budget_infeasible.json",
        "trace_reduced_budget_infeasible.json",
        "response_updates.json"
    )

    foreach ($file in $expectedFiles) {
        $filePath = Join-Path $demoOut $file
        if (-not (Test-Path $filePath)) {
            throw "Expected output artifact missing: $file"
        }
    }

    # 7. Run W4 slice CLI command
    Write-Host "[7/8] Running W4 slice command..."
    $sliceOut = Join-Path $cloneDir "evaluation\results\w4\slice"
    & $venvPython -m src.cli slice --out $sliceOut --seed 20261024 --budget 10
    if ($LASTEXITCODE -ne 0) {
        throw "Slice command failed with exit code $LASTEXITCODE"
    }

    $expectedSliceFiles = @(
        "diagnostic_record.json",
        "manifest.json",
        "plan_assessment_failed.json",
        "plan_assessment_passed.json",
        "plan_learner1_day1.json",
        "plan_learner2_day1.json",
        "plan_missed_day.json",
        "plan_reduced_budget.json",
        "plan_remediation.json",
        "plan_review_due.json",
        "plan_shortened_deadline.json",
        "response_updates.json",
        "trace_assessment_failed.json",
        "trace_assessment_passed.json",
        "trace_learner1_day1.json",
        "trace_learner2_day1.json",
        "trace_missed_day.json",
        "trace_reduced_budget.json",
        "trace_remediation.json",
        "trace_review_due.json",
        "trace_shortened_deadline.json"
    )

    foreach ($file in $expectedSliceFiles) {
        $filePath = Join-Path $sliceOut $file
        if (-not (Test-Path $filePath)) {
            throw "Expected slice output artifact missing: $file"
        }
    }

    # 8. Run evaluate CLI command
    Write-Host "[8/8] Running evaluate command..."
    & git checkout -- evaluation/results 2>$null
    $evalOut = Join-Path $cloneDir "evaluation\results\w5\eval_clean"
    & $venvPython -m src.cli evaluate --config experiments/w5_integrated.yaml --out $evalOut --learners 2

    $expectedEvalFiles = @(
        "manifest.json",
        "per_learner.csv",
        "summary.md"
    )

    foreach ($file in $expectedEvalFiles) {
        $filePath = Join-Path $evalOut $file
        if (-not (Test-Path $filePath)) {
            throw "Expected evaluate output artifact missing: $file"
        }
    }

    Write-Host "=========================================================="
    Write-Host "PASS: Clean run verified successfully on SHA $Sha."
    Write-Host "All tests passed and all artifacts (14 demo, 21 slice, 3 evaluate) verified."
    Write-Host "=========================================================="
    Pop-Location
    Remove-Item -Recurse -Force $cloneDir -ErrorAction SilentlyContinue
    exit 0
} catch {
    Write-Host "=========================================================="
    Write-Host "FAIL: $_"
    Write-Host "=========================================================="
    try {
        Pop-Location
    } catch {}
    Remove-Item -Recurse -Force $cloneDir -ErrorAction SilentlyContinue
    exit 1
}
