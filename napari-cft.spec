# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for napari-cft.

Usage:
    pip install pyinstaller
    pyinstaller napari-cft.spec

This will produce a bundled app in dist/napari-cft/
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

block_cipher = None

# ── Binaries ────────────────────────────────────────────────────────────
# imagecodecs loads codec extension modules lazily — PyInstaller misses them
import importlib, glob
_ic_dir = os.path.dirname(importlib.import_module('imagecodecs').__file__)
binaries = [
    (so, 'imagecodecs')
    for so in glob.glob(os.path.join(_ic_dir, '*.so'))
    + glob.glob(os.path.join(_ic_dir, '*.pyd'))
]

# ── Data files ──────────────────────────────────────────────────────────
# These are non-Python files that napari loads at runtime.
datas = []

# napari resources: icons, logos, fonts, loading.gif, etc.
datas += collect_data_files('napari', subdir='resources')

# Qt stylesheets (.qss files)
datas += collect_data_files('napari', subdir='_qt/qt_resources/styles')

# napari_builtins plugin manifest
datas += collect_data_files('napari_builtins')

# vispy needs its shaders, fonts, color maps
datas += collect_data_files('vispy')

# debugpy vendored files (needed for IPython console)
datas += collect_data_files('debugpy')

# imageio needs its plugin configs
datas += collect_data_files('imageio')

# magicgui / app_model
datas += collect_data_files('magicgui')
datas += collect_data_files('app_model')

# npe2 plugin framework
datas += collect_data_files('npe2')

# Package metadata (needed for entry_points / plugin discovery)
# Include ALL installed packages' metadata so entry_points work in the bundle
_metadata_packages = [
    'napari', 'napari-svg', 'napari-console', 'napari-itk-io',
    'napari-plugin-engine', 'napari-imagecodecs', 'imagecodecs',
    'napari_builtins', 'cft-zarr',
    'vispy', 'imageio', 'npe2', 'magicgui', 'app-model',
    'scikit-image', 'scipy', 'dask', 'zarr', 'Pillow', 'tifffile',
    'pydantic', 'psygnal', 'superqt', 'qtpy', 'PySide6',
]
for _pkg in _metadata_packages:
    try:
        datas += copy_metadata(_pkg, recursive=True)
    except Exception:
        pass  # package may be bundled inside another or not separately installed

# napari plugin data files (yaml manifests etc.)
for _plugin in ['napari_svg', 'napari_console', 'napari_itk_io', 'cft_zarr']:
    try:
        datas += collect_data_files(_plugin)
    except Exception:
        pass

# Template files used at runtime (not collected automatically)
import napari
_napari_pkg = Path(napari.__file__).parent
datas += [(str(_napari_pkg / 'utils' / 'add_layer.py_tmpl'), 'napari/utils')]

# ── Hidden imports ──────────────────────────────────────────────────────
# Modules that napari imports dynamically at runtime.
hiddenimports = []

# Scientific stack — napari lazy-imports many submodules
hiddenimports += collect_submodules('scipy.ndimage')
hiddenimports += collect_submodules('scipy.spatial')
hiddenimports += collect_submodules('scipy.interpolate')
hiddenimports += collect_submodules('scipy.sparse')
hiddenimports += collect_submodules('scipy.stats')
hiddenimports += collect_submodules('scipy.linalg')
hiddenimports += collect_submodules('skimage.morphology')
hiddenimports += collect_submodules('skimage.measure')
hiddenimports += collect_submodules('skimage.draw')
hiddenimports += collect_submodules('skimage.transform')
hiddenimports += collect_submodules('skimage.color')
hiddenimports += collect_submodules('skimage.util')
hiddenimports += collect_submodules('skimage.data')

# Image I/O
hiddenimports += collect_submodules('imageio')
hiddenimports += ['PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.PngImagePlugin']
hiddenimports += ['tifffile']

# Lazy arrays
hiddenimports += ['dask', 'dask.array', 'dask.delayed']
hiddenimports += ['zarr']

# Vispy — rendering
hiddenimports += collect_submodules('vispy')

# Qt binding (pick whichever you use — PySide6 is typical for recent napari)
hiddenimports += collect_submodules('qtpy')
# Uncomment the one you use:
# hiddenimports += collect_submodules('PyQt5')
# hiddenimports += collect_submodules('PyQt6')
# hiddenimports += collect_submodules('PySide2')
hiddenimports += collect_submodules('PySide6')

# UI frameworks
hiddenimports += collect_submodules('magicgui')
hiddenimports += collect_submodules('app_model')

# Plugin system
hiddenimports += collect_submodules('npe2')
hiddenimports += collect_submodules('napari_builtins')
hiddenimports += collect_submodules('napari_svg')
hiddenimports += collect_submodules('napari_console')
hiddenimports += ['napari_itk_io']
hiddenimports += ['napari_imagecodecs']
hiddenimports += ['cft_zarr']

# Settings / config (dynamically loaded via __import__)
hiddenimports += ['yaml', 'json']

# Pydantic
hiddenimports += ['pydantic', 'pydantic.v1']
hiddenimports += ['typing_extensions']

# Napari itself — the lazy_loader means many submodules aren't found
hiddenimports += collect_submodules('napari')

# Optional: numba acceleration (comment out if you don't use it)
# hiddenimports += collect_submodules('numba')

# Optional: triangulation backends (include whichever you have installed)
# hiddenimports += ['bermuda']
# hiddenimports += ['triangle']

# ── Analysis ────────────────────────────────────────────────────────────
a = Analysis(
    ['src/napari/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_napari.py'],
    excludes=[
        # Exclude test modules to reduce size
        'pytest',
        'napari._tests',
        'napari.benchmarks',
        'hypothesis',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='napari-cft',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app, no terminal
    icon='src/napari/resources/icon.icns' if sys.platform == 'darwin' else 'src/napari/resources/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='napari-cft',
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='napari-cft.app',
        icon='src/napari/resources/icon.icns',
        bundle_identifier='com.napari-cft.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'NSSupportsAutomaticGraphicsSwitching': True,
        },
    )
