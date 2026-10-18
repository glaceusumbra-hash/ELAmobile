import os
import sys
import subprocess

# =========================================================================
# AUTO-REPARADOR DE ENTORNO FLET (Se ejecuta solo si falta el motor)
# =========================================================================
try:
    import flet as ft
    if not hasattr(ft, "app"):
        raise AttributeError
except (ImportError, AttributeError):
    print("\n[*] Reparando Flet en tu entorno virtual... (espera 15 segundos)")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "flet==0.24.1", "opencv-python", "pillow", "numpy", "piexif"])
    print("[+] Reparación completada con éxito. Abriendo aplicación...\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import io
import json
import time
import base64
import hashlib
from datetime import datetime


class ForensicEngine:
    def __init__(self, quality=90, scale=15.0):
        self.quality = quality
        self.scale = scale

    def compute_ela(self, image_bgr):
        im_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_orig = Image.fromarray(im_rgb)

        buf = io.BytesIO()
        pil_orig.save(buf, 'JPEG', quality=self.quality)
        buf.seek(0)
        pil_resaved = Image.open(buf)

        diff = ImageChops.difference(pil_orig, pil_resaved)
        ela_amplified = ImageEnhance.Brightness(diff).enhance(self.scale)
        ela_rgb = np.array(ela_amplified)
        ela_gray = cv2.cvtColor(ela_rgb, cv2.COLOR_RGB2GRAY)

        return ela_rgb, ela_gray

    def generate_sweep(self, ela_rgb, ela_gray, sweep_mode, threshold=45):
        norm = np.clip(ela_gray.astype(np.float32) * (255.0 / max(threshold, 1)), 0, 255).astype(np.uint8)

        if sweep_mode == "JET":
            sweep_bgr = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
            return cv2.cvtColor(sweep_bgr, cv2.COLOR_BGR2RGB)
        elif sweep_mode == "INFERNO":
            sweep_bgr = cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)
            return cv2.cvtColor(sweep_bgr, cv2.COLOR_BGR2RGB)
        elif sweep_mode == "HOT":
            sweep_bgr = cv2.applyColorMap(norm, cv2.COLORMAP_HOT)
            return cv2.cvtColor(sweep_bgr, cv2.COLOR_BGR2RGB)
        else:
            return ela_rgb

    @staticmethod
    def mat_to_base64(img_array, is_bgr=False):
        rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB) if is_bgr else img_array
        pil_img = Image.fromarray(rgb)
        buff = io.BytesIO()
        pil_img.save(buff, format="JPEG", quality=85)
        return base64.b64encode(buff.getvalue()).decode("utf-8")


def main(page: ft.Page):
    page.title = "MacBook Pro 16\" - ELA Forensic Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#071224"
    page.padding = 20
    page.window_min_width = 1100
    page.window_min_height = 700

    engine = ForensicEngine()

    state = {
        "raw_bgr": None,
        "ela_rgb": None,
        "ela_gray": None,
        "active_sweep_rgb": None,
        "active_mode": "JET",
        "threshold": 45,
        "manifest": {}
    }

    # Cuadro 1: Upload
    img_view1 = ft.Image(fit=ft.ImageFit.CONTAIN, expand=True)
    box_v1_content = ft.Container(
        content=ft.Column(
            [
                ft.Text("⬡ 🔍", size=48, color="#cbd5e1"),
                ft.Text("sube  tu  imagen", size=20, weight=ft.FontWeight.BOLD, color="#cbd5e1")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center,
        expand=True
    )

    # Cuadro 2: ELA Frame
    img_view2 = ft.Image(fit=ft.ImageFit.CONTAIN, expand=True)
    box_v2_content = ft.Container(
        content=ft.Column(
            [
                ft.Text("📷 ⇄", size=48, color="#cbd5e1"),
                ft.Text("ELA analitic  farme", size=20, weight=ft.FontWeight.BOLD, color="#cbd5e1")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center,
        expand=True
    )

    # Cuadros de texto
    txt_ela_data = ft.Text("Esperando archivo para análisis de error...", font_family="monospace", size=11, color="#94a3b8")
    txt_metadata = ft.Text("Esperando análisis de metadatos...", font_family="monospace", size=11, color="#a7f3d0")

    def update_revelation():
        if state["raw_bgr"] is None:
            return

        sweep_rgb = engine.generate_sweep(
            state["ela_rgb"], state["ela_gray"], state["active_mode"], state["threshold"]
        )
        state["active_sweep_rgb"] = sweep_rgb

        img_view2.src_base64 = engine.mat_to_base64(sweep_rgb, is_bgr=False)
        box_v2_content.content = img_view2

        _, mask = cv2.threshold(state["ela_gray"], state["threshold"], 255, cv2.THRESH_BINARY)
        tampered_px = cv2.countNonZero(mask)
        total_px = state["raw_bgr"].shape[0] * state["raw_bgr"].shape[1]
        ratio = (tampered_px / total_px) * 100
        sha = hashlib.sha256(mask.tobytes()).hexdigest()

        txt_ela_data.value = (
            f"MODO ACTIVO: {state['active_mode']}\n"
            f"CALIDAD JPEG BASE: 90%\n"
            f"AMPLIFICACIÓN: 15.0x\n"
            f"THRESHOLD DE CORTE: {state['threshold']}\n"
            f"PÍXELES EN DISCORDANCIA: {tampered_px:,}\n"
            f"RATIO DE MANIPULACIÓN: {ratio:.4f}%\n"
            f"HUELLA SHA-256:\n{sha[:32]}...\n"
            f"DIAGNÓSTICO: {'ALTERACIÓN DETECTADA' if ratio > 0.08 else 'INTEGRO'}"
        )
        page.update()

    def set_sweep(mode_name):
        state["active_mode"] = mode_name
        update_revelation()

    def on_file_loaded(e: ft.FilePickerResultEvent):
        if not e.files:
            return

        file_path = e.files[0].path
        state["raw_bgr"] = cv2.imread(file_path)

        state["ela_rgb"], state["ela_gray"] = engine.compute_ela(state["raw_bgr"])

        img_view1.src_base64 = engine.mat_to_base64(state["raw_bgr"], is_bgr=True)
        box_v1_content.content = img_view1

        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        realtime_ns = time.time_ns()
        monotonic_ns = time.monotonic_ns()
        token = hashlib.sha256(f"{realtime_ns}:{monotonic_ns}".encode('utf-8')).hexdigest()[:12]

        software_traces = []
        for s in [b"Photoshop", b"GIMP", b"Canva", b"Lightroom", b"Figma"]:
            if s.lower() in raw_bytes.lower():
                software_traces.append(s.decode('latin-1'))

        meta = {
            "device_security_token": token,
            "hardware_timestamp_utc": datetime.utcfromtimestamp(realtime_ns / 1e9).isoformat() + "Z",
            "device_monotonic_clock": monotonic_ns,
            "detected_software_footprints": software_traces if software_traces else "None",
            "source_dimensions": f"{state['raw_bgr'].shape[1]}x{state['raw_bgr'].shape[0]} px",
            "execution_environment": "FLET_CROSSPLATFORM_LOCAL"
        }
        state["manifest"] = meta
        txt_metadata.value = json.dumps(meta, indent=2)

        update_revelation()

    def export_evidence(_):
        if state["raw_bgr"] is None or not state["manifest"]:
            return

        out_dir = "forensic_exports"
        os.makedirs(out_dir, exist_ok=True)
        token = state["manifest"].get("device_security_token", "DUMP")
        base = f"{out_dir}/DUMP_{token}_{int(time.time())}"

        with open(f"{base}_manifest.json", "w", encoding="utf-8") as f:
            json.dump(state["manifest"], f, indent=2)

        cv2.imwrite(f"{base}_raw.png", state["raw_bgr"])
        cv2.imwrite(f"{base}_sweep_{state['active_mode']}.png", cv2.cvtColor(state["active_sweep_rgb"], cv2.COLOR_BGR2RGB))

        page.snack_bar = ft.SnackBar(ft.Text(f"Evidencia exportada en {out_dir}/"))
        page.snack_bar.open = True
        page.update()

    file_picker = ft.FilePicker(on_result=on_file_loaded)
    page.overlay.append(file_picker)

    def make_circle_btn(color_hex, mode_key):
        return ft.Container(
            width=36,
            height=36,
            border_radius=18,
            bgcolor=color_hex,
            on_click=lambda _: set_sweep(mode_key),
            ink=True
        )

    # 1. Columna 1
    col_1 = ft.Column(
        [
            ft.Container(
                content=box_v1_content,
                border=ft.border.all(2, ft.colors.WHITE),
                border_radius=2,
                bgcolor="#0b172a",
                expand=True
            ),
            ft.Container(
                content=ft.ElevatedButton(
                    "🖥️  up load",
                    on_click=lambda _: file_picker.pick_files(allow_multiple=False),
                    style=ft.ButtonStyle(
                        bgcolor="#1e293b",
                        color="#ffffff",
                        shape=ft.RoundedRectangleBorder(radius=6),
                        side=ft.BorderSide(1, "#475569")
                    ),
                    height=36,
                    width=140
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10)
            )
        ],
        expand=10
    )

    # 2. Columna 2
    col_2 = ft.Column(
        [
            ft.Container(
                content=box_v2_content,
                border=ft.border.all(2, ft.colors.WHITE),
                border_radius=2,
                bgcolor="#0b172a",
                expand=True
            ),
            ft.Container(
                content=ft.Row(
                    [
                        make_circle_btn("#22c55e", "JET"),
                        make_circle_btn("#a855f7", "INFERNO"),
                        make_circle_btn("#f97316", "HOT"),
                        make_circle_btn("#eab308", "ELA_RGB")
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12
                ),
                padding=ft.padding.only(top=10)
            )
        ],
        expand=10
    )

    # 3. Columna 3
    col_3 = ft.Column(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("ErrorLevelAnalisis Data:", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        ft.Container(content=txt_ela_data, expand=True)
                    ],
                    spacing=8
                ),
                border=ft.border.all(2, ft.colors.WHITE),
                border_radius=2,
                bgcolor="#0b172a",
                padding=15,
                expand=4
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("metadata reserch", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        ft.Container(content=txt_metadata, expand=True),
                        ft.Container(
                            content=ft.ElevatedButton(
                                "🖥️  Export",
                                on_click=export_evidence,
                                style=ft.ButtonStyle(
                                    bgcolor="#1f5159",
                                    color="#ffffff",
                                    shape=ft.RoundedRectangleBorder(radius=6),
                                    side=ft.BorderSide(1, "#5eead4")
                                ),
                                height=34,
                                width=130
                            ),
                            alignment=ft.alignment.center,
                            padding=ft.padding.only(bottom=5)
                        )
                    ],
                    spacing=8
                ),
                border=ft.border.all(2, ft.colors.WHITE),
                border_radius=2,
                bgcolor="#0d3238",
                padding=15,
                expand=5
            )
        ],
        expand=9,
        spacing=15
    )

    page.add(ft.Row([col_1, col_2, col_3], expand=True, spacing=20))


if __name__ == "__main__":
    ft.app(target=main)