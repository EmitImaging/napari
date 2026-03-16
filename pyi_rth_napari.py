"""PyInstaller runtime hook for napari.

When frozen, skip napari's macOS subprocess relaunch logic
by setting the env var that tells it the fixes already ran.
The PyInstaller bundle already has the right executable name.
"""
import os
import sys

if getattr(sys, 'frozen', False):
    os.environ['_NAPARI_RERUN_WITH_FIXES'] = '1'
