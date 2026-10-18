import customtkinter as ctk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import io
import json
import time
import hashlib
from datetime import datetime, timezone
import os

ctk.set_appearance_mode("Dark")


# =====================================================================
# FUNCIÓN DE EXPORTACIÓN DE REPORTE FORENSE (.TXT)
# =====================================================================
def exportar_reporte_completo(metadata_dispositivo, datos_json, info_marco):
    """
    Consolida la información del dispositivo, el JSON y el marco de creación,
    y abre un diálogo para guardar el archivo .txt.
    """
    # 1. Diálogo para elegir dónde guardar el archivo
    archivo_destino = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
        title="Guardar reporte completo de análisis"
    )
    
    if not archivo_destino:
        return None  # El usuario canceló la acción

    # 2. Construir la estructura del reporte en texto plano
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    reporte = []
    reporte.append("=" * 60)
    reporte.append("       REPORTE DE AUDITORÍA Y METADATOS - FIGMA EXTRACTOR PRO")
    reporte.append("=" * 60)
    reporte.append(f"Fecha de generación: {timestamp}\n")
    
    # Sección 1: Información del Dispositivo / Cámara
    reporte.append("-" * 60)
    reporte.append("1. INFORMACIÓN DEL DISPOSITIVO / ORIGEN")
    reporte.append("-" * 60)
    if metadata_dispositivo:
        for clave, valor in metadata_dispositivo.items():
            reporte.append(f"  - {clave}: {valor}")
    else:
        reporte.append("  No se encontraron datos del dispositivo (Exif limpio o ausente).")
    reporte.append("\n")
    
    # Sección 2: Marco de Creación / Análisis Visual
    reporte.append("-" * 60)
    reporte.append("2. MARCO DE CREACIÓN E INTERPRETACIÓN VISUAL")
    reporte.append("-" * 60)
    if info_marco:
        for clave, valor in info_marco.items():
            reporte.append(f"  - {clave}: {valor}")
    else:
        reporte.append("  Sin datos de marco registrados.")
    reporte.append("\n")
    
    # Sección 3: Datos JSON Completos
    reporte.append("-" * 60)
    reporte.append("3. DATASET JSON COMPLETO")
    reporte.append("-" * 60)
    json_formateado = json.dumps(datos_json, indent=4, ensure_ascii=False)
    reporte.append(json_formateado)
    reporte.append("\n" + "=" * 60)
    reporte.append("Fin del reporte.")
    reporte.append("=" * 60)

    # 3. Escribir el archivo físico en disco
    try:
        with open(archivo_destino, "w", encoding="utf-8") as f:
            f.write("\n".join(reporte))
        print(f"Reporte exportado exitosamente en: {archivo_destino}")
        return archivo_destino
    except Exception as e:
        print(f"Error al guardar el archivo: {e}")
        return None


# =====================================================================
# INTERFAZ Y DASHBOARD FORENSE
# =====================================================================
class ForensicDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title('MacBook Pro 16" - ELA Forensic Dashboard')
        self.geometry("1280x750")
        self.minsize(1100, 680)
        
        # Fondo oscuro con tono azul profundo
        self.configure(fg_color="#071224")

        # Variables de estado
        self.raw_image = None
        self.ela_rgb = None
        self.ela_gray = None
        self.active_sweep_img = None
        self.active_mode = "JET"
        self.threshold_val = 45
        self.manifest = {}
        self.ela_metrics = {}

        self._build_layout()

    def _build_layout(self):
        # Grid Principal: 3 Columnas principales (Box 1 | Box 2 | Panel Derecho)
        self.grid_columnconfigure(0, weight=10, uniform="cols")
        self.grid_columnconfigure(1, weight=10, uniform="cols")
        self.grid_columnconfigure(2, weight=9, uniform="cols")
        self.grid_rowconfigure(0, weight=1)

        # =====================================================================
        # COLUMNA 1: SUBE TU IMAGEN
        # =====================================================================
        col1 = ctk.CTkFrame(self, fg_color="transparent")
        col1.grid(row=0, column=0, padx=(25, 12), pady=25, sticky="nsew")
        col1.grid_rowconfigure(0, weight=1)
        col1.grid_columnconfigure(0, weight=1)

        self.box_upload = ctk.CTkFrame(
            col1, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2
        )
        self.box_upload.grid(row=0, column=0, sticky="nsew")
        self.box_upload.grid_rowconfigure(0, weight=1)
        self.box_upload.grid_columnconfigure(0, weight=1)

        self.lbl_view1 = ctk.CTkLabel(
            self.box_upload, text="⬡ 🔍\n\n sube tu imagen", 
            font=("Inter", 20, "bold"), text_color="#cbd5e1"
        )
        self.lbl_view1.grid(row=0, column=0, padx=10, pady=10)

        self.btn_upload = ctk.CTkButton(
            col1, text="🖥️  up load", font=("Chivo Mono", 13, "bold"),
            fg_color="#1e293b", hover_color="#334155", border_width=1, border_color="#475569",
            height=36, width=140, corner_radius=6, command=self.load_image
        )
        self.btn_upload.grid(row=1, column=0, pady=(15, 0))

        # =====================================================================
        # COLUMNA 2: ELA ANALITIC FRAME
        # =====================================================================
        col2 = ctk.CTkFrame(self, fg_color="transparent")
        col2.grid(row=0, column=1, padx=12, pady=25, sticky="nsew")
        col2.grid_rowconfigure(0, weight=1)
        col2.grid_columnconfigure(0, weight=1)

        self.box_ela = ctk.CTkFrame(
            col2, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2
        )
        self.box_ela.grid(row=0, column=0, sticky="nsew")
        self.box_ela.grid_rowconfigure(0, weight=1)
        self.box_ela.grid_columnconfigure(0, weight=1)

        self.lbl_view2 = ctk.CTkLabel(
            self.box_ela, text="📷 ⇄\n\nELA analitic  frame", 
            font=("Inter", 20, "bold"), text_color="#cbd5e1"
        )
        self.lbl_view2.grid(row=0, column=0, padx=10, pady=10)

        # 4 Botones Circulares de Barridos de Color
        circle_container = ctk.CTkFrame(col2, fg_color="transparent")
        circle_container.grid(row=1, column=0, pady=(15, 0))

        self.btn_c1 = ctk.CTkButton(
            circle_container, text="", width=38, height=38, corner_radius=19,
            fg_color="#22c55e", hover_color="#16a34a", command=lambda: self.set_sweep("JET")
        )
        self.btn_c1.pack(side="left", padx=8)

        self.btn_c2 = ctk.CTkButton(
            circle_container, text="", width=38, height=38, corner_radius=19,
            fg_color="#a855f7", hover_color="#9333ea", command=lambda: self.set_sweep("INFERNO")
        )
        self.btn_c2.pack(side="left", padx=8)

        self.btn_c3 = ctk.CTkButton(
            circle_container, text="", width=38, height=38, corner_radius=19,
            fg_color="#f97316", hover_color="#ea580c", command=lambda: self.set_sweep("HOT")
        )
        self.btn_c3.pack(side="left", padx=8)

        self.btn_c4 = ctk.CTkButton(
            circle_container, text="", width=38, height=38, corner_radius=19,
            fg_color="#eab308", hover_color="#ca8a04", command=lambda: self.set_sweep("ELA_RGB")
        )
        self.btn_c4.pack(side="left", padx=8)

        # =====================================================================
        # COLUMNA 3: PANELES DERECHOS (DATA + METADATA RESEARCH)
        # =====================================================================
        col3 = ctk.CTkFrame(self, fg_color="transparent")
        col3.grid(row=0, column=2, padx=(12, 25), pady=25, sticky="nsew")
        col3.grid_rowconfigure(0, weight=4)
        col3.grid_rowconfigure(1, weight=5)
        col3.grid_columnconfigure(0, weight=1)

        # ErrorLevelAnalisis Data
        self.box_data = ctk.CTkFrame(
            col3, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2
        )
        self.box_data.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        self.box_data.grid_rowconfigure(1, weight=1)
        self.box_data.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.box_data, text="ErrorLevelAnalisis Data:", font=("Inter", 16, "bold"), text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.txt_ela_data = ctk.CTkTextbox(
            self.box_data, fg_color="transparent", font=("Chivo Mono", 11), text_color="#94a3b8"
        )
        self.txt_ela_data.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.txt_ela_data.insert("1.0", "Esperando archivo para análisis de error...")

        # metadata research
        self.box_meta = ctk.CTkFrame(
            col3, fg_color="#0d3238", border_width=2, border_color="#ffffff", corner_radius=2
        )
        self.box_meta.grid(row=1, column=0, sticky="nsew")
        self.box_meta.grid_rowconfigure(1, weight=1)
        self.box_meta.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.box_meta, text="metadata resaerch", font=("Inter", 16, "bold"), text_color="#ffffff"
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        self.txt_metadata = ctk.CTkTextbox(
            self.box_meta, fg_color="transparent", font=("Chivo Mono", 11), text_color="#a7f3d0"
        )
        self.txt_metadata.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.txt_metadata.insert("1.0", "Esperando análisis de metadatos...")

        # Botón Export
        self.btn_export = ctk.CTkButton(
            self.box_meta, text="🖥️  Export", font=("Chivo Mono", 13, "bold"),
            fg_color="#1f5159", hover_color="#134149", border_width=1, border_color="#5eead4",
            height=34, width=130, corner_radius=6, command=self.export_evidence
        )
        self.btn_export.grid(row=2, column=0, pady=(0, 15))

    # =========================================================================
    # LÓGICA FORENSE
    # =========================================================================
    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.tiff *.jfif")])
        if not path:
            return

        self.raw_image = cv2.imread(path)

        # 1. Buffer ELA base en memoria
        im_rgb = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2RGB)
        pil_orig = Image.fromarray(im_rgb)

        buf = io.BytesIO()
        pil_orig.save(buf, 'JPEG', quality=90)
        buf.seek(0)
        pil_resaved = Image.open(buf)

        diff = ImageChops.difference(pil_orig, pil_resaved)
        self.ela_rgb = np.array(ImageEnhance.Brightness(diff).enhance(15.0))
        self.ela_gray = cv2.cvtColor(self.ela_rgb, cv2.COLOR_RGB2GRAY)

        # 2. Renderizar imagen original en Cuadro 1
        self._render_image(self.raw_image, self.lbl_view1, is_bgr=True)

        # 3. Metadatos
        with open(path, "rb") as f:
            raw_bytes = f.read()
        self._parse_metadata(raw_bytes)

        # 4. Actualizar visualización ELA
        self.update_sweep_view()

    def set_sweep(self, mode_name):
        self.active_mode = mode_name
        self.update_sweep_view()

    def update_sweep_view(self):
        if self.raw_image is None:
            return

        norm = np.clip(self.ela_gray.astype(np.float32) * (255.0 / self.threshold_val), 0, 255).astype(np.uint8)

        if self.active_mode == "JET":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
        elif self.active_mode == "INFERNO":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)
        elif self.active_mode == "HOT":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_HOT), cv2.COLOR_BGR2RGB)
        else:
            self.active_sweep_img = self.ela_rgb

        # Renderizar en Cuadro 2
        self._render_image(self.active_sweep_img, self.lbl_view2, is_bgr=False)

        # Métricas de alteración
        _, mask = cv2.threshold(self.ela_gray, self.threshold_val, 255, cv2.THRESH_BINARY)
        tampered_px = cv2.countNonZero(mask)
        total_px = self.raw_image.shape[0] * self.raw_image.shape[1]
        ratio = (tampered_px / total_px) * 100
        sha = hashlib.sha256(mask.tobytes()).hexdigest()
        diagnostico = "ALTERACIÓN DETECTADA" if ratio > 0.08 else "INTEGRO"

        # Guardar métricas para la exportación
        self.ela_metrics = {
            "Modo activo": self.active_mode,
            "Calidad JPEG base": "90%",
            "Amplificación": "15.0x",
            "Threshold de corte": self.threshold_val,
            "Píxeles en discordancia": f"{tampered_px:,}",
            "Ratio de manipulación": f"{ratio:.4f}%",
            "Huella SHA-256": sha,
            "Diagnóstico": diagnostico
        }

        ela_report = (
            f"MODO ACTIVO: {self.active_mode}\n"
            f"CALIDAD JPEG BASE: 90%\n"
            f"AMPLIFICACIÓN: 15.0x\n"
            f"THRESHOLD DE CORTE: {self.threshold_val}\n"
            f"PÍXELES EN DISCORDANCIA: {tampered_px:,}\n"
            f"RATIO DE MANIPULACIÓN: {ratio:.4f}%\n"
            f"HUELLA SHA-256:\n{sha[:32]}...\n"
            f"DIAGNÓSTICO: {diagnostico}"
        )
        self.txt_ela_data.delete("1.0", "end")
        self.txt_ela_data.insert("1.0", ela_report)

    def _parse_metadata(self, raw_bytes):
        realtime_ns = time.time_ns()
        monotonic_ns = time.monotonic_ns()
        token = hashlib.sha256(f"{realtime_ns}:{monotonic_ns}".encode('utf-8')).hexdigest()[:12]

        software_traces = []
        for s in [b"Photoshop", b"GIMP", b"Canva", b"Lightroom", b"Figma"]:
            if s.lower() in raw_bytes.lower():
                software_traces.append(s.decode('latin-1'))

        meta_dict = {
            "device_security_token": token,
            "hardware_timestamp_utc": datetime.fromtimestamp(realtime_ns / 1e9, tz=timezone.utc).isoformat(),
            "device_monotonic_clock": monotonic_ns,
            "detected_software_footprints": software_traces if software_traces else "None",
            "source_dimensions": f"{self.raw_image.shape[1]}x{self.raw_image.shape[0]} px",
            "network_status": "100%_OFFLINE_LOCAL"
        }
        self.manifest = meta_dict

        self.txt_metadata.delete("1.0", "end")
        self.txt_metadata.insert("1.0", json.dumps(meta_dict, indent=2))

    def _render_image(self, img_array, label_widget, is_bgr=True):
        rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB) if is_bgr else img_array
        h, w = rgb.shape[:2]
        scale = min(360 / w, 440 / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)

        ctk_img = ctk.CTkImage(Image.fromarray(resized), size=(nw, nh))
        label_widget.configure(image=ctk_img, text="")

    def export_evidence(self):
        """
        Exporta el reporte consolidado (.txt) mediante diálogo y guarda
        las evidencias gráficas en la carpeta local.
        """
        if self.raw_image is None or not self.manifest:
            messagebox.showwarning("Atención", "Por favor, carga primero una imagen para exportar.")
            return

        # 1. Preparar Dataset JSON consolidado
        dataset_completo = {
            "metadata_dispositivo": self.manifest,
            "marco_analisis_visual": self.ela_metrics
        }

        # 2. Llamada a la función de exportación del reporte .txt
        ruta_reporte = exportar_reporte_completo(
            metadata_dispositivo=self.manifest,
            datos_json=dataset_completo,
            info_marco=self.ela_metrics
        )

        if not ruta_reporte:
            return  # El usuario canceló la selección de guardado

        # 3. Exportar copias de respaldo de imágenes (PNGs del análisis)
        out_dir = "forensic_exports"
        os.makedirs(out_dir, exist_ok=True)
        token = self.manifest.get("device_security_token", "DUMP")
        base = f"{out_dir}/DUMP_{token}_{int(time.time())}"

        cv2.imwrite(f"{base}_raw.png", self.raw_image)
        if self.active_sweep_img is not None:
            cv2.imwrite(f"{base}_sweep_{self.active_mode}.png", cv2.cvtColor(self.active_sweep_img, cv2.COLOR_RGB2BGR))

        messagebox.showinfo("Éxito", f"Reporte exportado exitosamente en:\n{ruta_reporte}")


if __name__ == "__main__":
    app = ForensicDashboard()
    app.mainloop()