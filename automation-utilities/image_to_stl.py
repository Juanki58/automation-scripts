"""
Convierte una imagen (color o B/N) en un STL en relieve.
Requiere: opencv-python, numpy
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_IMAGE = SCRIPT_DIR / "castillo.jpg"
DEFAULT_STL = SCRIPT_DIR / "castillo_3d.stl"


def _is_grayscale(img_bgr: np.ndarray, sat_threshold: float = 30.0) -> bool:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 1])) < sat_threshold


def _outer_background_mask(binary: np.ndarray) -> np.ndarray:
    """Marca el fondo exterior inundando desde las esquinas por pixeles oscuros."""
    h, w = binary.shape
    flood = cv2.bitwise_not(binary)
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if flood[y, x] > 0:
            cv2.floodFill(flood, None, (x, y), 64)
    return flood == 64


def _height_map_bw(
    img_bgr: np.ndarray,
    base_mm: float = 2.0,
    relief_mm: float = 3.0,
) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    outer = _outer_background_mask(binary)
    shield = ~outer

    height_map = np.zeros(gray.shape, dtype=np.float32)
    height_map[shield] = base_mm
    height_map[shield & (binary == 255)] = base_mm + relief_mm
    return height_map


def _height_map_color(img_bgr: np.ndarray) -> np.ndarray:
    h, w, _ = img_bgr.shape
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    height_map = np.zeros((h, w), dtype=np.float32)

    def get_color_mask(rgb_img, target_color, tolerance=35):
        diff = np.linalg.norm(rgb_img - np.array(target_color, dtype=np.float32), axis=2)
        return diff < tolerance

    mask_blue = get_color_mask(img_rgb, [1, 110, 143])
    mask_yellow = get_color_mask(img_rgb, [236, 188, 80])
    mask_red = get_color_mask(img_rgb, [225, 47, 57])

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
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
    return height_map


def _write_stl(facets: list, output_stl_path: str) -> None:
    with open(output_stl_path, "wb") as f:
        f.write(b"\x00" * 80)
        f.write(np.uint32(len(facets)).tobytes())
        for normal, v1, v2, v3 in facets:
            data = np.array(normal + v1 + v2 + v3, dtype=np.float32)
            f.write(data.tobytes())
            f.write(b"\x00\x00")


def image_to_stl(
    image_path: str,
    output_stl_path: str,
    pixel_size_mm: float = 0.3,
    mode: str = "auto",
    base_mm: float = 2.0,
    relief_mm: float = 3.0,
    max_dim: int = 500,
) -> bool:
    print("Cargando y analizando imagen...")
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: no se pudo leer la imagen en '{image_path}'")
        return False

    h0, w0 = img.shape[:2]
    if max_dim > 0 and max(h0, w0) > max_dim:
        scale = max_dim / float(max(h0, w0))
        img = cv2.resize(
            img,
            (max(1, int(w0 * scale)), max(1, int(h0 * scale))),
            interpolation=cv2.INTER_AREA,
        )
        print(f"Imagen redimensionada: {w0}x{h0} -> {img.shape[1]}x{img.shape[0]}")

    use_bw = mode == "bw" or (mode == "auto" and _is_grayscale(img))
    if use_bw:
        print(f"Modo B/N: negro={base_mm} mm, blanco={base_mm + relief_mm} mm")
        height_map = _height_map_bw(img, base_mm=base_mm, relief_mm=relief_mm)
    else:
        print("Modo color: segmentacion por tonos del escudo")
        height_map = _height_map_color(img)

    h, w = height_map.shape
    print("Generando geometria 3D y calculando caras...")

    facets = []

    def add_triangle(v1, v2, v3):
        facets.append(([0.0, 0.0, 1.0], v1, v2, v3))

    for y in range(h - 1):
        for x in range(w - 1):
            z00 = float(height_map[y, x])
            z10 = float(height_map[y + 1, x])
            z01 = float(height_map[y, x + 1])
            z11 = float(height_map[y + 1, x + 1])

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
    _write_stl(facets, output_stl_path)
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
    parser.add_argument(
        "--mode",
        choices=("auto", "bw", "color"),
        default="auto",
        help="auto detecta B/N o color; bw fuerza blanco alto / negro bajo",
    )
    parser.add_argument("--base-mm", type=float, default=2.0, help="Altura base B/N (negro)")
    parser.add_argument("--relief-mm", type=float, default=3.0, help="Relieve extra B/N (blanco)")
    parser.add_argument(
        "--max-dim",
        type=int,
        default=500,
        help="Lado maximo en px (0 = sin redimensionar)",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: coloca la imagen en '{args.image}' o indica otra ruta.")
        print("Ejemplo: python image_to_stl.py castillo.jpg -o castillo_3d.stl --mode bw")
        raise SystemExit(1)

    ok = image_to_stl(
        args.image,
        args.output,
        pixel_size_mm=args.pixel_size,
        mode=args.mode,
        base_mm=args.base_mm,
        relief_mm=args.relief_mm,
        max_dim=args.max_dim,
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
