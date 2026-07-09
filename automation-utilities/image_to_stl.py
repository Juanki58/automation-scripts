"""
Convierte el escudo de El Vendrell (u otra imagen en color) en un STL en relieve.
Requiere: opencv-python, numpy
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_IMAGE = SCRIPT_DIR / "image_8ff221.png"
DEFAULT_STL = SCRIPT_DIR / "escudo_vendrell_3d.stl"


def image_to_stl(image_path: str, output_stl_path: str, pixel_size_mm: float = 0.4) -> bool:
    print("Cargando y analizando imagen...")
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: no se pudo leer la imagen en '{image_path}'")
        return False

    h, w, _ = img.shape
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    height_map = np.zeros((h, w), dtype=np.float32)

    def get_color_mask(rgb_img, target_color, tolerance=35):
        diff = np.linalg.norm(rgb_img - np.array(target_color, dtype=np.float32), axis=2)
        return diff < tolerance

    mask_blue = get_color_mask(img_rgb, [1, 110, 143])
    mask_yellow = get_color_mask(img_rgb, [236, 188, 80])
    mask_red = get_color_mask(img_rgb, [225, 47, 57])

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

    background_mask = thresh.copy()
    cv2.floodFill(background_mask, None, (10, 10), 128)
    outer_background = background_mask == 128
    inner_white = (thresh == 255) & (~outer_background)

    height_map[~outer_background] = 2.0
    height_map[inner_white] = 2.0
    height_map[mask_blue] = 3.5
    height_map[mask_red] = 4.5
    height_map[mask_yellow] = 5.5

    print("Generando geometria 3D y calculando caras...")

    facets = []

    def add_triangle(v1, v2, v3):
        normal = [0.0, 0.0, 1.0]
        facets.append((normal, v1, v2, v3))

    for y in range(h - 1):
        for x in range(w - 1):
            z00 = height_map[y, x]
            z10 = height_map[y + 1, x]
            z01 = height_map[y, x + 1]
            z11 = height_map[y + 1, x + 1]

            if z00 == 0 and z10 == 0 and z01 == 0 and z11 == 0:
                continue

            px0, px1 = x * pixel_size_mm, (x + 1) * pixel_size_mm
            py0, py1 = (h - y) * pixel_size_mm, (h - (y + 1)) * pixel_size_mm

            v00 = [px0, py0, z00]
            v10 = [px0, py1, z10]
            v01 = [px1, py0, z01]
            v11 = [px1, py1, z11]

            add_triangle(v00, v10, v11)
            add_triangle(v00, v11, v01)

    print(f"Guardando STL en: {output_stl_path}")
    with open(output_stl_path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(np.uint32(len(facets)).tobytes())

        for normal, v1, v2, v3 in facets:
            data = np.array(normal + v1 + v2 + v3, dtype=np.float32)
            f.write(data.tobytes())
            f.write(b"\x00\x00")

    print(f"Proceso completado. Caras creadas: {len(facets)}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Convierte una imagen en relieve a STL")
    parser.add_argument(
        "image",
        nargs="?",
        default=str(DEFAULT_IMAGE),
        help="Ruta de la imagen de entrada (PNG/JPG)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_STL),
        help="Ruta del archivo STL de salida",
    )
    parser.add_argument(
        "--pixel-size",
        type=float,
        default=0.3,
        help="Tamano en mm de cada pixel (default: 0.3)",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: coloca la imagen en '{args.image}' o indica otra ruta.")
        print("Ejemplo: python image_to_stl.py mi_escudo.png -o escudo.stl --pixel-size 0.3")
        raise SystemExit(1)

    ok = image_to_stl(args.image, args.output, pixel_size_mm=args.pixel_size)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
