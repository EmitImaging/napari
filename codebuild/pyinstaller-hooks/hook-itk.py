from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)


# ITK loads generated Python wrappers from real files on disk relative to the
# package directory, so collecting the package only into PYZ is not enough.
datas = [
    entry
    for entry in collect_data_files("itk", include_py_files=True)
    if "__pycache__" not in entry[0]
]
binaries = collect_dynamic_libs("itk")
hiddenimports = collect_submodules("itk")
datas += copy_metadata("itk", recursive=True)
