from importlib import metadata as importlib_metadata

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

# `itk` is often a namespace package assembled from multiple wheel
# distributions (for example `itk-core`, `itk-numerics`, etc.), so there may
# be no distribution literally named `itk`. Copy metadata for any discovered
# backing distributions on a best-effort basis.
for dist_name in importlib_metadata.packages_distributions().get("itk", []):
    try:
        datas += copy_metadata(dist_name, recursive=True)
    except Exception:
        pass
