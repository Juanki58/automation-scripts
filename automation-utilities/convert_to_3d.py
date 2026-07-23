"""Descarga el escudo de El Vendrell y lo convierte a STL 3D."""

import argparse
from pathlib import Path

import requests

from image_to_stl import image_to_stl

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_URL = "https://images.prodia.xyz/8ff221ec-6d8c-4f7f-bf2a-43d9229f3d9d.png"
DEFAULT_IMAGE = SCRIPT_DIR / "image_8ff221.png"
DEFAULT_STL = SCRIPT_DIR / "escudo_vendrell_3d.stl"


def download_image(url: str, dest: Path) -> bool:
    print("Descargando imagen del escudo...")
    try:
        response = requests.get(
            url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 (compatible; B-Intelligent/1.0)"},
        )
        response.raise_for_status()
        if len(response.content) < 1000:
            print("Error: la URL devolvio un archivo demasiado pequeno (posiblemente expirada).")
            return False
        dest.write_bytes(response.content)
        print(f"Imagen guardada en {dest} ({len(response.content):,} bytes)")
        return True
    except requests.RequestException as exc:
        print(f"Error al descargar: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Descarga escudo PNG y genera STL en relieve")
    parser.add_argument(
        "image",
        nargs="?",
        default=DEFAULT_IMAGE,
        help="Ruta local de la imagen (default: image_8ff221.png)",
    )
    parser.add_argument("-o", "--output", default=DEFAULT_STL, help="STL de salida")
    parser.add_argument("--pixel-size", type=float, default=0.3, help="Tamano mm/pixel")
    parser.add_argument("--mode", choices=("auto", "bw", "color"), default="auto")
    parser.add_argument("--thickness-mm", type=float, default=2.5, help="Grosor material B/N")
    parser.add_argument(
        "--print-white",
        action="store_true",
        help="Imprime blanco y deja negro vacio (por defecto: blanco no se imprime)",
    )
    parser.add_argument("--max-dim", type=int, default=500, help="Lado maximo px (0=sin limite)")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL de descarga si falta la imagen local")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="No intentar descargar; exige que la imagen local exista",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.is_absolute():
        image_path = SCRIPT_DIR / image_path
    if not image_path.exists():
        if args.skip_download:
            print(f"Error: no existe '{image_path}'")
            raise SystemExit(1)
        if not download_image(args.url, image_path):
            print()
            print("Alternativa: guarda la imagen manualmente como:")
            print(f"  {image_path.resolve()}")
            print("y vuelve a ejecutar: python convert_to_3d.py")
            raise SystemExit(1)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = SCRIPT_DIR / output_path
    ok = image_to_stl(
        str(image_path),
        str(output_path),
        pixel_size_mm=args.pixel_size,
        mode=args.mode,
        thickness_mm=args.thickness_mm,
        white_cutout=not args.print_white,
        max_dim=args.max_dim,
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
