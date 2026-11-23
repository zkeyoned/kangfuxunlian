# 在 Windows 上构建康师复桌面包，产出 dist\KangShiFu\KangShiFu.exe。
#
# 依赖装在仓库外的独立虚拟环境里，产物写在仓库外的目录里，都不入库。
# 训练辅助，非医疗诊断。
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (Resolve-Path (Join-Path $here "..\..")).Path
$venv = if ($env:REHAB_BUILD_VENV) { $env:REHAB_BUILD_VENV } else { Join-Path $env:USERPROFILE ".venvs\rehab-desktop-build" }
$out  = if ($env:REHAB_BUILD_OUT)  { $env:REHAB_BUILD_OUT }  else { Join-Path $env:LOCALAPPDATA "rehab-desktop-build" }
$py   = if ($env:REHAB_BUILD_PYTHON) { $env:REHAB_BUILD_PYTHON } else { "py -3.12" }

function Say($text) { Write-Host "`n==== $text" }

$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Say "创建构建虚拟环境 $venv"
  Invoke-Expression "$py -m venv `"$venv`""
  $pipArgs = @()
  if ($env:REHAB_PIP_INDEX) { $pipArgs = @("-i", $env:REHAB_PIP_INDEX) }
  # 版本与 algorithm\rehab-pose-demo\requirements*.txt 保持一致。
  # rtmlib 必须 --no-deps：它同时声明了两个 OpenCV 包，会装出重复的 cv2。
  # mediapipe 与 av 不装：本机 rtmpose 路径用不到。
  & $venvPython -m pip install @pipArgs numpy==2.5.3 opencv-contrib-python==5.0.0.93 onnxruntime==1.30.0 tqdm==4.70.1
  & $venvPython -m pip install @pipArgs --no-deps rtmlib==0.0.16
  & $venvPython -m pip install @pipArgs pyinstaller pywebview
}

Say "准备模型权重"
if ($env:REHAB_MODELS_FROM) {
  & $venvPython (Join-Path $here "fetch_models.py") --from $env:REHAB_MODELS_FROM
} else {
  & $venvPython (Join-Path $here "fetch_models.py")
}
if ($LASTEXITCODE -ne 0) { throw "模型准备或校验失败" }

Say "清理旧产物"
Remove-Item -Recurse -Force (Join-Path $out "build"), (Join-Path $out "dist") -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

Say "PyInstaller 构建"
Push-Location $repo
& (Join-Path $venv "Scripts\pyinstaller.exe") --noconfirm --clean `
  --distpath (Join-Path $out "dist") --workpath (Join-Path $out "build") `
  (Join-Path $here "rehab-desktop.spec")
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败" }

$app = Join-Path $out "dist\KangShiFu"
if (-not (Test-Path (Join-Path $app "KangShiFu.exe"))) { throw "构建没有产出 KangShiFu.exe" }

Say "生成启动快捷批处理"
$startBat = @"
@echo off
rem 双击这里启动康师复。
start "" "%~dp0KangShiFu.exe"
"@
$browserBat = @"
@echo off
rem 内嵌窗口里摄像头用不了时双击这个文件，改用系统默认浏览器打开训练页面。
start "" "%~dp0KangShiFu.exe" --ui browser
"@
Set-Content -Path (Join-Path $app "双击这里启动康师复.bat") -Value $startBat -Encoding Default
Set-Content -Path (Join-Path $app "以浏览器模式启动.bat") -Value $browserBat -Encoding Default

Say "打包成 zip"
$zip = Join-Path $out "dist\康师复-windows-x64.zip"
Remove-Item -Force $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $app -DestinationPath $zip

Say "构建完成"
Write-Host ("产物目录：" + (Join-Path $out "dist"))
Write-Host ("自检：" + (Join-Path $app "KangShiFu.exe") + " --selftest")
