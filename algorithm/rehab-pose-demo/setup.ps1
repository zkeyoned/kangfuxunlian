$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements-rtmpose.txt
if ($LASTEXITCODE -ne 0) { throw 'ONNX installation failed.' }
& .\.venv\Scripts\python.exe -m pip install --no-deps rtmlib==0.0.16
if ($LASTEXITCODE -ne 0) { throw 'RTMLib installation failed.' }
& .\.venv\Scripts\python.exe -m rehab_pose.run --download-model
if ($LASTEXITCODE -ne 0) { throw 'Model download failed. See README for manual setup.' }
& .\.venv\Scripts\python.exe -m rehab_pose.run --backend rtmpose --download-model
if ($LASTEXITCODE -ne 0) { throw 'RTMPose model download failed.' }
Write-Host 'Ready. Run .\.venv\Scripts\python.exe app.py'
