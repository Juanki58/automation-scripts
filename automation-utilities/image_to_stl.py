"""
Convierte una imagen (color o B/N) en un STL en relieve.
Requiere: opencv-python, numpy
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_IMAGE = SCRIPT_DIR / "escudo3.0.jpeg"
DEFAULT_STL = SCRIPT_DIR / "escudo3.0_3d.stl"


def _is_grayscale(img_bgr: np.ndarray, sat_threshold: float = 30.0) -> bool:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 1])) < sat_threshold


def _height_map_bw(
    img_bgr: np.ndarray,
    thickness_mm: float = 2.5,
    white_cutout: bool = True,
) -> np.ndarray:
    """B/N: por defecto el blanco no se imprime (altura 0) y el negro si."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    height_map = np.zeros(gray.shape, dtype=np.float32)
    if white_cutout:
        # Blanco = hueco; negro = material
        height_map[binary == 0] = thickness_mm
    else:
        height_map[binary == 255] = thickness_mm
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


def _add_triangle(facets: list, v1, v2, v3) -> None:
    facets.append(([0.0, 0.0, 1.0], v1, v2, v3))


def _add_quad(facets: list, a, b, c, d) -> None:
    _add_triangle(facets, a, b, c)
    _add_triangle(facets, a, c, d)


def _mesh_solid_voxels(height_map: np.ndarray, pixel_size_mm: float) -> list:
    """Prisma solido por pixel con altura > 0 (el blanco/0 no genera geometria)."""
    facets = []
    h, w = height_map.shape

    for y in range(h):
        for x in range(w):
            z = float(height_map[y, x])
            if z <= 0:
                continue

            x0, x1 = x * pixel_size_mm, (x + 1) * pixel_size_mm
            y0, y1 = (h - y) * pixel_size_mm, (h - (y + 1)) * pixel_size_mm

            # Cara superior (z) e inferior (0)
            _add_quad(
                facets,
                [x0, y0, z],
                [x0, y1, z],
                [x1, y1, z],
                [x1, y0, z],
            )
            _add_quad(
                facets,
                [x0, y0, 0.0],
                [x1, y0, 0.0],
                [x1, y1, 0.0],
                [x0, y1, 0.0],
            )

            # Paredes solo donde el vecino esta vacio (ahorra caras internas)
            if x == 0 or height_map[y, x - 1] <= 0:
                _add_quad(
                    facets,
                    [x0, y0, 0.0],
                    [x0, y1, 0.0],
                    [x0, y1, z],
                    [x0, y0, z],
                )
            if x == w - 1 or height_map[y, x + 1] <= 0:
                _add_quad(
                    facets,
                    [x1, y0, 0.0],
                    [x1, y0, z],
                    [x1, y1, z],
                    [x1, y1, 0.0],
                )
            if y == 0 or height_map[y - 1, x] <= 0:
                _add_quad(
                    facets,
                    [x0, y0, 0.0],
                    [x0, y0, z],
                    [x1, y0, z],
                    [x1, y0, 0.0],
                )
            if y == h - 1 or height_map[y + 1, x] <= 0:
                _add_quad(
                    facets,
                    [x0, y1, 0.0],
                    [x1, y1, 0.0],
                    [x1, y1, z],
                    [x0, y1, z],
                )

    return facets


def _mesh_height_surface(height_map: np.ndarray, pixel_size_mm: float) -> list:
    """Malla de superficie (modo color / relieve continuo)."""
    facets = []
    h, w = height_map.shape

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

            _add_triangle(
                facets,
                [px0, py0, z00],
                [px0, py1, z10],
                [px1, py1, z11],
            )
            _add_triangle(
                facets,
                [px0, py0, z00],
                [px1, py1, z11],
                [px1, py0, z01],
            )

    return facets


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
    thickness_mm: float = 2.5,
    white_cutout: bool = True,
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
        if white_cutout:
            print(f"Modo B/N: blanco=sin imprimir, negro={thickness_mm} mm")
        else:
            print(f"Modo B/N invertido: negro=sin imprimir, blanco={thickness_mm} mm")
        height_map = _height_map_bw(
            img,
            thickness_mm=thickness_mm,
            white_cutout=white_cutout,
        )
        print("Generando geometria solida (prismas)...")
        facets = _mesh_solid_voxels(height_map, pixel_size_mm)
    else:
        print("Modo color: segmentacion por tonos del escudo")
        height_map = _height_map_color(img)
        print("Generando geometria 3D y calculando caras...")
        facets = _mesh_height_surface(height_map, pixel_size_mm)

    if not facets:
        print("Error: no se genero geometria. Revisa contraste blanco/negro de la imagen.")
        return False

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
        help="auto detecta B/N o color",
    )
    parser.add_argument(
        "--thickness-mm",
        type=float,
        default=2.5,
        help="Grosor del material en mm (zonas que se imprimen)",
    )
    parser.add_argument(
        "--print-white",
        action="store_true",
        help="Imprime el blanco y deja el negro vacio (por defecto es al reves)",
    )
    parser.add_argument(
        "--max-dim",
        type=int,
        default=500,
        help="Lado maximo en px (0 = sin redimensionar)",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: coloca la imagen en '{args.image}' o indica otra ruta.")
        print(
            "Ejemplo: python image_to_stl.py escudo3.0.jpeg -o escudo3.0_3d.stl --mode bw"
        )
        raise SystemExit(1)

    ok = image_to_stl(
        args.image,
        args.output,
        pixel_size_mm=args.pixel_size,
        mode=args.mode,
        thickness_mm=args.thickness_mm,
        white_cutout=not args.print_white,
        max_dim=args.max_dim,
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
