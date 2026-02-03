from __future__ import annotations

import base64
import numpy as np

from napari.utils.colormaps.colormap import Colormap

# Generate from Fiji's fire.lut (768 bytes):
#   python -c "import base64; print(base64.b64encode(open('fire.lut','rb').read()).decode())"
_FIJI_FIRE_LUT_B64 = "AAAAAAAAAAAAAAAAAAAAAAEEBwoNEBMWGRwfIiUoKy4xNDc6PUBDRklMT1JVWFteYmVoa25xdHd6fYCDhomMj5KUlpianJ6goqOkpqeoqqutrq+xsrO1tri5ury9vsDBw8TGx8nKzM3P0NHS1NXW19na3N3f4OLj5ebn6err7e7w8fP09vf5+vz8/P39/f7+/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAwUHCAoMDhATFRgbHSAjJSgrLjAzNjk7PkFERklMT1FUV1pcX2JlZ2lrbW9xc3V3eXt9f4GDhYaIioyNj5GTlJaYmpudn6GipKaoqautr7CytLa4ury+v8HDxcfJy83O0NLU1dfZ29ze4OLk5ujq6+3v8fL09vj4+fr7/P3+//////////////////////////////////////////8ABw8WHiYtNT1BRUpOUldbYGRobHF1eX2ChoqPk5ecoKWoq6+ytbm8wMPHys7R1djc3N3e3+Dh4uPg3tza2NbU0s7Kx8O/vLi1sa2ppqKempeTj4yIhIF9enZyb2tnZGBdWVVSTkpHQ0A8ODUxLSomIx8bFxQQDAgFBAMDAgEBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQIDREVGh4jKjI6QkpSWmJpcXmBiJCYoKevt7/Hz9ff4+fr7/P3+///////////"

def fiji_fire() -> Colormap:
    raw = base64.b64decode(_FIJI_FIRE_LUT_B64)
    if len(raw) != 768:
        raise ValueError(f"Expected 768 bytes for Fiji LUT, got {len(raw)}")

    lut = np.frombuffer(raw, dtype=np.uint8)
    r = lut[0:256]
    g = lut[256:512]
    b = lut[512:768]

    rgb = np.stack([r, g, b], axis=1).astype(np.float32) / 255.0
    a = np.ones((256, 1), dtype=np.float32)
    rgba = np.concatenate([rgb, a], axis=1)  # (256, 4)

    return Colormap(colors=rgba, name="fire", display_name="fire")