$ErrorActionPreference = "Stop"
Set-Location $env:CODEBUILD_SRC_DIR
function Step { param([string]$m); Write-Host "`n==== $m ====" -ForegroundColor Cyan }
function Fail { param([string]$m); Write-Error $m; exit 1 }
function Check { param([string]$m); if ($LASTEXITCODE -ne 0) { Fail $m } }

$env:PYTHONUTF8 = "1"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PIP_NO_PYTHON_VERSION_WARNING = "1"
$env:GIT_TERMINAL_PROMPT = "0"
$env:PIP_CACHE_DIR = Join-Path $env:CODEBUILD_SRC_DIR $env:PIP_CACHE_DIR
New-Item -ItemType Directory -Force $env:PIP_CACHE_DIR | Out-Null
if (-not (Test-Path ".\pyproject.toml") -or -not (Test-Path ".\src\napari\__init__.py")) { Fail "This is not a napari source tree." }
if ([string]::IsNullOrWhiteSpace($env:NAPARI_CFT_SRC_REPO_URL)) { Fail "NAPARI_CFT_SRC_REPO_URL is not set." }

Step "Checking out napari-cft"
$CftDir = Join-Path $env:CODEBUILD_SRC_DIR "src\cft"
if (Test-Path $CftDir) { Remove-Item $CftDir -Recurse -Force }
$Clone = @("clone", "--progress", "--single-branch")
if ($env:NAPARI_CFT_SRC_CLONE_DEPTH) { $Clone += @("--depth", $env:NAPARI_CFT_SRC_CLONE_DEPTH) }
if ($env:NAPARI_CFT_SRC_BRANCH) { $Clone += @("--branch", $env:NAPARI_CFT_SRC_BRANCH) }
& git @Clone $env:NAPARI_CFT_SRC_REPO_URL $CftDir; Check "Could not clone napari-cft."
if (-not (Test-Path "$CftDir\__init__.py")) { Fail "src\cft\__init__.py was not found." }

Step "Creating virtual environment"
if (Test-Path $env:VENV_DIR) { Remove-Item $env:VENV_DIR -Recurse -Force }
python --version
where.exe python
python -m venv $env:VENV_DIR; Check "Could not create virtual environment."
$Py = Join-Path $env:CODEBUILD_SRC_DIR "$($env:VENV_DIR)\Scripts\python.exe"
if (-not (Test-Path $Py)) { Fail "Build Python was not found." }
& $Py -m pip install --upgrade pip setuptools wheel packaging; Check "Could not upgrade packaging tools."

$Requested = if ($env:BUILD_TORCH_FLAVOR) { $env:BUILD_TORCH_FLAVOR.Trim().ToLowerInvariant() } else { "cpu" }
$TorchFlavor = if ($Requested -eq "gpu") { if ($env:GPU_TORCH_FLAVOR) { $env:GPU_TORCH_FLAVOR.Trim().ToLowerInvariant() } else { "cu128" } } else { $Requested }
$Index = switch ($TorchFlavor) {
  "cpu" { "https://download.pytorch.org/whl/cpu" }
  "cu118" { "https://download.pytorch.org/whl/cu118" }
  "cu126" { "https://download.pytorch.org/whl/cu126" }
  "cu128" { "https://download.pytorch.org/whl/cu128" }
  default { Fail "Unsupported BUILD_TORCH_FLAVOR: $Requested" }
}

Step "Installing dependencies ($TorchFlavor)"
& $Py -m pip install torch torchvision --index-url $Index; Check "Could not install PyTorch."
& $Py -m pip install -e ".[${env:QT_BACKEND},sam2]" antspyx "napari-plugin-manager>=0.1.9,<0.2.0" "napari-svg>=0.1.8" "napari-itk-io>=0.4.1" imageio-ffmpeg pyinstaller; Check "Could not install build dependencies."
& $Py -c "import ants,itk,napari,napari_itk_io,napari_plugin_manager,sam2,torch,imageio_ffmpeg; from importlib.resources import files; assert files('napari_builtins').joinpath('builtins.yaml').is_file(); print('Dependencies OK:',torch.__version__,torch.version.cuda)"; Check "Dependency verification failed."

$Version = (& $Py -c "from importlib.metadata import version; from packaging.version import Version; print(Version(version('napari')).base_version)").Trim()
if (-not $Version) { Fail "Could not resolve napari version." }
$AppName = "$($env:APP_BASE_NAME)-$Version-cft.$($env:CFT_VERSION)"
$ArtifactName = "$AppName-$TorchFlavor"
Step "Building $AppName"
@(
  'from __future__ import annotations'
  'import runpy,sys'
  'from pathlib import Path'
  'def main():'
  '    args=sys.argv[1:]'
  '    if args and args[0]=="--run-script":'
  '        path=Path(args[1]).resolve(); sys.argv=[str(path),*args[2:]]; sys.path.insert(0,str(path.parent)); runpy.run_path(str(path),run_name="__main__"); return 0'
  '    from napari.__main__ import main as napari_main'
  '    return int(napari_main() or 0)'
  'raise SystemExit(main())'
) | Set-Content .\launch_napari_cft.py -Encoding ASCII
Remove-Item .\build,.\dist,".\$AppName.spec" -Recurse -Force -ErrorAction SilentlyContinue
$Pyi = @(
  "--noconfirm","--console","--name",$AppName,"--additional-hooks-dir","codebuild\pyinstaller-hooks"
  "--collect-all","napari","--collect-all","napari_builtins","--collect-all","cft","--collect-all","ants","--collect-all","itk","--collect-all","imageio_ffmpeg"
  "--collect-all","scipy","--collect-all","dask","--collect-all","magicgui","--collect-all","vispy","--collect-all","qtpy","--collect-all","superqt","--collect-all","napari_plugin_engine","--collect-all","npe2"
  "--collect-all","napari_console","--collect-all","napari_plugin_manager","--collect-all","napari_svg","--collect-all","napari_itk_io","--collect-all","napari_imagecodecs","--collect-all","imagecodecs","--collect-all","sam2","--collect-all","s3fs"
  "--copy-metadata","napari","--copy-metadata","napari-plugin-engine","--copy-metadata","napari-plugin-manager","--copy-metadata","napari-svg","--copy-metadata","napari-itk-io","--copy-metadata","napari-imagecodecs","--copy-metadata","antspyx","--copy-metadata","imagecodecs","--copy-metadata","sam2","--copy-metadata","torch","--copy-metadata","torchvision","--copy-metadata","npe2","--copy-metadata","imageio","--copy-metadata","imageio-ffmpeg","--copy-metadata","s3fs","--copy-metadata","tifffile"
  "--hidden-import","torch","--hidden-import","torchvision","launch_napari_cft.py"
)
if ($env:QT_BACKEND -in @("pyqt","pyqt6")) { $Pyi += @("--hidden-import","PyQt6","--hidden-import","PyQt6.QtCore","--hidden-import","PyQt6.QtGui","--hidden-import","PyQt6.QtWidgets") }
if ($env:QT_BACKEND -in @("pyside","pyside6")) { $Pyi += @("--hidden-import","PySide6","--hidden-import","PySide6.QtCore","--hidden-import","PySide6.QtGui","--hidden-import","PySide6.QtWidgets") }
& $Py -m PyInstaller @Pyi; Check "PyInstaller failed."

$Dist = Join-Path $env:CODEBUILD_SRC_DIR "dist\$AppName"
if (-not (Test-Path "$Dist\_internal\itk\ITKPyBasePython.py")) { Fail "Bundled ITK runtime is missing." }
$Exe = Get-ChildItem $Dist -Filter "*.exe" -File | Select-Object -First 1
if (-not $Exe) { Fail "Bundled napari executable was not found." }
@('import dask,scipy,napari_builtins,napari_itk_io,napari_plugin_manager,torch','from importlib.resources import files','assert files("napari_builtins").joinpath("builtins.yaml").is_file()','print("Packaged plugins, SciPy, Dask, and torch OK")') | Set-Content .\verify_packaged.py -Encoding ASCII
& $Exe.FullName --run-script .\verify_packaged.py; Check "Packaged runtime validation failed."

Step "Compressing artifact"
$ZipName = "$ArtifactName-windows-x64.zip"
$Zip = Join-Path $env:CODEBUILD_SRC_DIR "dist\$ZipName"
& tar.exe -a -c -f $Zip -C (Split-Path $Dist -Parent) (Split-Path $Dist -Leaf); Check "Could not create zip artifact."
if (-not (Test-Path $Zip)) { Fail "Zip artifact was not created: $Zip" }
$UpdateLatest = @("1","true","yes","y","on") -contains $env:UPDATE_LATEST.Trim().ToLowerInvariant()
$LatestFlavor = "$($env:APP_BASE_NAME)-cft-$TorchFlavor-windows-x64.zip"
$Kind = if ($TorchFlavor -eq "cpu") { "cpu" } else { "gpu" }
$LatestKind = "$($env:APP_BASE_NAME)-cft-$Kind-windows-x64.zip"
if ($UpdateLatest) { Copy-Item $Zip (Join-Path $env:CODEBUILD_SRC_DIR "dist\$LatestFlavor"); if ($LatestKind -ne $LatestFlavor) { Copy-Item $Zip (Join-Path $env:CODEBUILD_SRC_DIR "dist\$LatestKind") } }
$ZipName | Set-Content .\dist\artifact_zip_name.txt -Encoding ASCII

if ($env:BUILD_ARTIFACTS_BUCKET) {
  $Ref = if ($env:CODEBUILD_WEBHOOK_HEAD_REF) { $env:CODEBUILD_WEBHOOK_HEAD_REF -replace '^refs/heads/','' } elseif ($env:CODEBUILD_SOURCE_VERSION -and $env:CODEBUILD_SOURCE_VERSION -notmatch '^[0-9a-f]{40}$') { $env:CODEBUILD_SOURCE_VERSION } else { "manual" }
  $Prefix = if ($env:BUILD_ARTIFACTS_PREFIX) { $env:BUILD_ARTIFACTS_PREFIX.TrimEnd('/') } else { "napari-cft" }
  $Base = "s3://$env:BUILD_ARTIFACTS_BUCKET/$Prefix/$Ref"
  aws s3 cp $Zip "$Base/$ZipName"; Check "Could not upload artifact."
  if ($UpdateLatest) { aws s3 cp $Zip "$Base/latest/$ZipName"; aws s3 cp $Zip "$Base/latest/$LatestFlavor"; if ($LatestKind -ne $LatestFlavor) { aws s3 cp $Zip "$Base/latest/$LatestKind" }; Check "Could not upload latest artifact." }
}
