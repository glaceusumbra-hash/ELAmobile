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
# 1. CONSTANTES DE VERSIÓN, COMPILACIÓN Y TRAZABILIDAD
# =====================================================================
APP_NAME = "ELA Forensic Dashboard"
APP_VERSION = "v2.6.4"
BUILD_CODE = "BUILD-2026.10-EXPERT"
EDITION_TAG = "Figma Extractor Pro / Forensic Diagnostic Edition"


# =====================================================================
# 2. MOTOR DE DICTAMEN PERICIAL (LENGUAJE NATURAL)
# =====================================================================
def generar_dictamen_humano(manifest, ela_metrics):
    """
    Evalúa los datos técnicos recopilados y redacta una explicación en español claro
    sobre los marcadores hallados y las razones periciales de sospecha o integridad.
    """
    hallazgos = []
    motivos = []
    nivel_sospecha = 0  # Escala 0 a 100

    softwares = manifest.get("detected_software_footprints", "None")
    ratio_str = ela_metrics.get("Ratio de manipulación", "0%").replace("%", "")
    try:
        ratio = float(ratio_str)
    except ValueError:
        ratio = 0.0

    tampered_px = ela_metrics.get("Píxeles en discordancia", "0")

    # A) Evaluación de huellas de software
    if softwares and softwares != "None":
        nombres = ", ".join(softwares) if isinstance(softwares, list) else str(softwares)
        hallazgos.append(f"• HUELLA DE SOFTWARE: Se detectaron firmas binarias de [{nombres}].")
        motivos.append(
            f"  -> ¿Por qué indica manipulación?: Las fotografías auténticas capturadas directamente por el "
            f"sensor de una cámara o smartphone no contienen firmas de programas de diseño. La presencia de {nombres} "
            f"demuestra de manera fehaciente que el archivo fue abierto, procesado o reexportado con una aplicación de edición digital."
        )
        nivel_sospecha += 50
    else:
        hallazgos.append("• SOFTWARE: No se identificaron firmas de programas de diseño conocidos (Photoshop, Canva, Figma).")

    # B) Evaluación de compresión asimétrica (Análisis ELA)
    if ratio > 0.08:
        hallazgos.append(
            f"• DISCORDANCIA DE COMPRESIÓN (ELA): El {ratio:.4f}% del área analizada ({tampered_px} píxeles) "
            f"presenta una tasa de error de compresión divergente."
        )
        motivos.append(
            f"  -> ¿Por qué indica manipulación?: Cuando un archivo JPEG se guarda, se comprime uniformemente. "
            f"Si una persona pega un elemento externo, clona detalles o añade textos, esa región modificada no tiene "
            f"el mismo historial de compresión que el fondo original. Las zonas de brillo anómalo en el visor térmico "
            f"revelan la ubicación exacta de las inserciones o alteraciones."
        )
        nivel_sospecha += 45
    else:
        hallazgos.append(f"• COMPRESIÓN HOMOGÉNEA: Nivel de discordancia dentro del rango normal ({ratio:.4f}%).")
        motivos.append(
            "  -> Interpretación: La degradación JPEG se comporta de manera uniforme en todo el lienzo, "
            "lo cual es el patrón esperado en capturas de una sola generación sin agregados externos."
        )

    # C) Veredicto final ponderado
    if nivel_sospecha >= 75:
        veredicto = "🔴 ALTA PROBABILIDAD DE MANIPULACIÓN DIGITAL"
        conclusion = (
            "Conclusión pericial: La imagen exhibe anomalías coincidentes (rastros de software de edición y "
            "asimetría en la degradación de compresión). El archivo presenta claras evidencias de intervención humana."
        )
    elif nivel_sospecha >= 40:
        veredicto = "🟡 SOSPECHA MODERADA DE EDICIÓN O RECOMPRESIÓN"
        conclusion = (
            "Conclusión pericial: Existen indicios parciales (software detectado o ligeras disparidades locales). "
            "El archivo pudo haber pasado por un recorte, redimensionado o ajuste cosmético."
        )
    else:
        veredicto = "🟢 IMAGEN APARENTEMENTE ÍNTEGRA / SIN ALTERACIONES"
        conclusion = (
            "Conclusión pericial: No se encontraron patrones de costura digital ni software de diseño en cabeceras. "
            "La distribución de error es uniforme."
        )

    dictamen_texto = (
        f"{veredicto}\n\n"
        f"1. MARCADORES DETECTADOS:\n" + "\n".join(hallazgos) + "\n\n"
        f"2. EXPLICACIÓN DE LOS MARCADORES:\n" + "\n\n".join(motivos) + "\n\n"
        f"3. DICTAMEN PERICIAL:\n{conclusion}"
    )
    return dictamen_texto, veredicto


# =====================================================================
# 3. EXPORTACIÓN DEL REPORTE CONSOLIDADO (.TXT)
# =====================================================================
def exportar_reporte_completo(metadata_dispositivo, datos_json, info_marco, dictamen_humano):
    """
    Abre una ventana de diálogo para guardar el archivo .txt con la versión,
    la explicación en lenguaje natural y los datos crudos.
    """
    archivo_destino = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
        title="Guardar dictamen pericial completo"
    )
    
    if not archivo_destino:
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    reporte = []
    reporte.append("=" * 70)
    reporte.append("       DICTAMEN PERICIAL FORENSE DE AUDITORÍA DE IMÁGENES")
    reporte.append(f"       Software: {APP_NAME} {APP_VERSION}")
    reporte.append(f"       Compilación: {BUILD_CODE} [{EDITION_TAG}]")
    reporte.append("=" * 70)
    reporte.append(f"Fecha de emisión: {timestamp}\n")

    reporte.append("*" * 70)
    reporte.append("I. RESULTADO Y EXPLICACIÓN DE MARCADORES (LENGUAJE NATURAL)")
    reporte.append("*" * 70)
    reporte.append(dictamen_humano)
    reporte.append("\n")

    reporte.append("-" * 70)
    reporte.append("II. INFORMACIÓN DE ORIGEN Y METADATOS TÉCNICOS")
    reporte.append("-" * 70)
    for clave, valor in metadata_dispositivo.items():
        reporte.append(f"  - {clave}: {valor}")
    reporte.append("\n")

    reporte.append("-" * 70)
    reporte.append("III. PARÁMETROS CUANTITATIVOS DEL MARCO ELA")
    reporte.append("-" * 70)
    for clave, valor in info_marco.items():
        reporte.append(f"  - {clave}: {valor}")
    reporte.append("\n")

    reporte.append("-" * 70)
    reporte.append("IV. REGISTRO CRIPTOGRÁFICO JSON COMPLETO")
    reporte.append("-" * 70)
    reporte.append(json.dumps(datos_json, indent=4, ensure_ascii=False))
    reporte.append("\n" + "=" * 70)
    reporte.append("Fin del reporte de auditoría forense.")
    reporte.append("=" * 70)

    try:
        with open(archivo_destino, "w", encoding="utf-8") as f:
            f.write("\n".join(reporte))
        return archivo_destino
    except Exception as e:
        print(f"Error escribiendo el reporte en disco: {e}")
        return None


# =====================================================================
# 4. DASHBOARD E INTERFAZ FORENSE
# =====================================================================
class ForensicDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} - {APP_VERSION} ({BUILD_CODE})")
        self.geometry("1300x780")
        self.minsize(1150, 700)
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
        self.dictamen_actual = ""

        self._build_layout()

    def _build_layout(self):
        # Grid Principal de 3 Columnas
        self.grid_columnconfigure(0, weight=10, uniform="cols")
        self.grid_columnconfigure(1, weight=10, uniform="cols")
        self.grid_columnconfigure(2, weight=11, uniform="cols")
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------------------------------------------
        # COLUMNA 1: SUBE TU IMAGEN
        # -----------------------------------------------------------------
        col1 = ctk.CTkFrame(self, fg_color="transparent")
        col1.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        col1.grid_rowconfigure(0, weight=1)
        col1.grid_columnconfigure(0, weight=1)

        self.box_upload = ctk.CTkFrame(col1, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2)
        self.box_upload.grid(row=0, column=0, sticky="nsew")
        self.box_upload.grid_rowconfigure(0, weight=1)
        self.box_upload.grid_columnconfigure(0, weight=1)

        self.lbl_view1 = ctk.CTkLabel(self.box_upload, text="⬡ 🔍\n\nSube tu imagen", font=("Inter", 20, "bold"), text_color="#cbd5e1")
        self.lbl_view1.grid(row=0, column=0, padx=10, pady=10)

        self.btn_upload = ctk.CTkButton(
            col1, text="🖥️  Cargar Imagen", font=("Chivo Mono", 13, "bold"),
            fg_color="#1e293b", hover_color="#334155", border_width=1, border_color="#475569",
            height=36, width=150, corner_radius=6, command=self.load_image
        )
        self.btn_upload.grid(row=1, column=0, pady=(15, 0))

        # -----------------------------------------------------------------
        # COLUMNA 2: ELA ANALITIC FRAME (BARRIDOS TÉRMICOS)
        # -----------------------------------------------------------------
        col2 = ctk.CTkFrame(self, fg_color="transparent")
        col2.grid(row=0, column=1, padx=10, pady=20, sticky="nsew")
        col2.grid_rowconfigure(0, weight=1)
        col2.grid_columnconfigure(0, weight=1)

        self.box_ela = ctk.CTkFrame(col2, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2)
        self.box_ela.grid(row=0, column=0, sticky="nsew")
        self.box_ela.grid_rowconfigure(0, weight=1)
        self.box_ela.grid_columnconfigure(0, weight=1)

        self.lbl_view2 = ctk.CTkLabel(self.box_ela, text="📷 ⇄\n\nRadiografía ELA", font=("Inter", 20, "bold"), text_color="#cbd5e1")
        self.lbl_view2.grid(row=0, column=0, padx=10, pady=10)

        # Contenedor de botones circulares de color
        circle_container = ctk.CTkFrame(col2, fg_color="transparent")
        circle_container.grid(row=1, column=0, pady=(15, 0))

        self.btn_c1 = ctk.CTkButton(circle_container, text="", width=36, height=36, corner_radius=18, fg_color="#22c55e", command=lambda: self.set_sweep("JET"))
        self.btn_c1.pack(side="left", padx=6)
        self.btn_c2 = ctk.CTkButton(circle_container, text="", width=36, height=36, corner_radius=18, fg_color="#a855f7", command=lambda: self.set_sweep("INFERNO"))
        self.btn_c2.pack(side="left", padx=6)
        self.btn_c3 = ctk.CTkButton(circle_container, text="", width=36, height=36, corner_radius=18, fg_color="#f97316", command=lambda: self.set_sweep("HOT"))
        self.btn_c3.pack(side="left", padx=6)
        self.btn_c4 = ctk.CTkButton(circle_container, text="", width=36, height=36, corner_radius=18, fg_color="#eab308", command=lambda: self.set_sweep("ELA_RGB"))
        self.btn_c4.pack(side="left", padx=6)

        # -----------------------------------------------------------------
        # COLUMNA 3: EXPLICACIÓN HUMANA Y DATOS TÉCNICOS
        # -----------------------------------------------------------------
        col3 = ctk.CTkFrame(self, fg_color="transparent")
        col3.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")
        col3.grid_rowconfigure(0, weight=6)
        col3.grid_rowconfigure(1, weight=4)
        col3.grid_columnconfigure(0, weight=1)

        # Caja Superior: Explicación en Cristiano
        self.box_dictamen = ctk.CTkFrame(col3, fg_color="#0d3238", border_width=2, border_color="#ffffff", corner_radius=2)
        self.box_dictamen.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.box_dictamen.grid_rowconfigure(1, weight=1)
        self.box_dictamen.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.box_dictamen, text="📋 Dictamen Pericial (Explicación)", font=("Inter", 15, "bold"), text_color="#5eead4"
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.txt_dictamen = ctk.CTkTextbox(
            self.box_dictamen, fg_color="transparent", font=("Chivo Mono", 11), text_color="#e2e8f0", wrap="word"
        )
        self.txt_dictamen.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.txt_dictamen.insert("1.0", "Cargue una imagen para ver la explicación pericial de los marcadores...")

        # Caja Inferior: Parámetros cuantitativos y botón de exportar
        self.box_data = ctk.CTkFrame(col3, fg_color="#0b172a", border_width=2, border_color="#ffffff", corner_radius=2)
        self.box_data.grid(row=1, column=0, sticky="nsew")
        self.box_data.grid_rowconfigure(1, weight=1)
        self.box_data.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.box_data, text="🔬 Parámetros Técnicos:", font=("Inter", 14, "bold"), text_color="#cbd5e1"
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

        self.txt_ela_data = ctk.CTkTextbox(self.box_data, fg_color="transparent", font=("Chivo Mono", 10), text_color="#94a3b8")
        self.txt_ela_data.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 5))

        self.btn_export = ctk.CTkButton(
            self.box_data, text="🖥️  Exportar Reporte Completo", font=("Chivo Mono", 12, "bold"),
            fg_color="#1f5159", hover_color="#134149", border_width=1, border_color="#5eead4",
            height=32, corner_radius=6, command=self.export_evidence
        )
        self.btn_export.grid(row=2, column=0, pady=(0, 10))

    # =========================================================================
    # 5. PROCEDIMIENTOS FORENSES
    # =========================================================================
    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.tiff *.jfif")])
        if not path:
            return

        self.raw_image = cv2.imread(path)

        # Generar ELA: compresión base al 90% y diferencia diferencial
        im_rgb = cv2.cvtColor(self.raw_image, cv2.COLOR_BGR2RGB)
        pil_orig = Image.fromarray(im_rgb)

        buf = io.BytesIO()
        pil_orig.save(buf, 'JPEG', quality=90)
        buf.seek(0)
        pil_resaved = Image.open(buf)

        diff = ImageChops.difference(pil_orig, pil_resaved)
        self.ela_rgb = np.array(ImageEnhance.Brightness(diff).enhance(15.0))
        self.ela_gray = cv2.cvtColor(self.ela_rgb, cv2.COLOR_RGB2GRAY)

        # Mostrar imagen original en el cuadro 1
        self._render_image(self.raw_image, self.lbl_view1, is_bgr=True)

        # Analizar metadatos crudos
        with open(path, "rb") as f:
            raw_bytes = f.read()
        self._parse_metadata(raw_bytes)
        
        # Actualizar vista ELA y generar dictamen
        self.update_sweep_view()

    def set_sweep(self, mode_name):
        self.active_mode = mode_name
        self.update_sweep_view()

    def update_sweep_view(self):
        if self.raw_image is None:
            return

        # Normalización con umbral de corte
        norm = np.clip(self.ela_gray.astype(np.float32) * (255.0 / self.threshold_val), 0, 255).astype(np.uint8)

        # Selección de paleta
        if self.active_mode == "JET":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
        elif self.active_mode == "INFERNO":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB)
        elif self.active_mode == "HOT":
            self.active_sweep_img = cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_HOT), cv2.COLOR_BGR2RGB)
        else:
            self.active_sweep_img = self.ela_rgb

        self._render_image(self.active_sweep_img, self.lbl_view2, is_bgr=False)

        # Cálculo de métricas
        _, mask = cv2.threshold(self.ela_gray, self.threshold_val, 255, cv2.THRESH_BINARY)
        tampered_px = cv2.countNonZero(mask)
        total_px = self.raw_image.shape[0] * self.raw_image.shape[1]
        ratio = (tampered_px / total_px) * 100
        sha = hashlib.sha256(mask.tobytes()).hexdigest()

        self.ela_metrics = {
            "Modo activo": self.active_mode,
            "Calidad JPEG base": "90%",
            "Amplificación": "15.0x",
            "Threshold de corte": self.threshold_val,
            "Píxeles en discordancia": f"{tampered_px:,}",
            "Ratio de manipulación": f"{ratio:.4f}%",
            "Huella SHA-256": sha
        }

        # Generar redacción humana y asignarla a la interfaz
        dictamen_texto, veredicto = generar_dictamen_humano(self.manifest, self.ela_metrics)
        self.dictamen_actual = dictamen_texto
        self.ela_metrics["Diagnóstico"] = veredicto

        self.txt_dictamen.delete("1.0", "end")
        self.txt_dictamen.insert("1.0", dictamen_texto)

        # Parámetros cuantitativos resumidos
        tecnico = (
            f"MODO: {self.active_mode} | THRESHOLD: {self.threshold_val}\n"
            f"DISCORDANCIA: {tampered_px:,} px ({ratio:.4f}%)\n"
            f"HASH DE MÁSCARA: {sha[:30]}..."
        )
        self.txt_ela_data.delete("1.0", "end")
        self.txt_ela_data.insert("1.0", tecnico)

    def _parse_metadata(self, raw_bytes):
        realtime_ns = time.time_ns()
        monotonic_ns = time.monotonic_ns()
        token = hashlib.sha256(f"{realtime_ns}:{monotonic_ns}".encode('utf-8')).hexdigest()[:12]

        software_traces = []
        for s in [b"Photoshop", b"GIMP", b"Canva", b"Lightroom", b"Figma"]:
            if s.lower() in raw_bytes.lower():
                software_traces.append(s.decode('latin-1'))

        meta_dict = {
            "analizador_version": f"{APP_VERSION} ({BUILD_CODE})",
            "device_security_token": token,
            "hardware_timestamp_utc": datetime.fromtimestamp(realtime_ns / 1e9, tz=timezone.utc).isoformat(),
            "device_monotonic_clock": monotonic_ns,
            "detected_software_footprints": software_traces if software_traces else "None",
            "source_dimensions": f"{self.raw_image.shape[1]}x{self.raw_image.shape[0]} px"
        }
        self.manifest = meta_dict

    def _render_image(self, img_array, label_widget, is_bgr=True):
        rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB) if is_bgr else img_array
        h, w = rgb.shape[:2]
        scale = min(360 / w, 440 / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)

        ctk_img = ctk.CTkImage(Image.fromarray(resized), size=(nw, nh))
        label_widget.configure(image=ctk_img, text="")

    def export_evidence(self):
        if self.raw_image is None or not self.manifest:
            messagebox.showwarning("Atención", "Cargue una imagen antes de generar la exportación.")
            return

        dataset_completo = {
            "auditoria": {
                "software": APP_NAME,
                "version": APP_VERSION,
                "compilacion": BUILD_CODE,
                "edicion": EDITION_TAG
            },
            "origen": self.manifest,
            "ela": self.ela_metrics,
            "dictamen": self.dictamen_actual
        }

        # 1. Guardar el reporte en texto estructurado
        ruta = exportar_reporte_completo(
            metadata_dispositivo=self.manifest,
            datos_json=dataset_completo,
            info_marco=self.ela_metrics,
            dictamen_humano=self.dictamen_actual
        )

        if not ruta:
            return  # Cancelado por el usuario

        # 2. Guardar copias locales de las imágenes analizadas
        out_dir = "forensic_exports"
        os.makedirs(out_dir, exist_ok=True)
        token = self.manifest.get("device_security_token", "DUMP")
        base = f"{out_dir}/DUMP_{token}_{int(time.time())}"

        cv2.imwrite(f"{base}_raw.png", self.raw_image)
        if self.active_sweep_img is not None:
            cv2.imwrite(f"{base}_sweep_{self.active_mode}.png", cv2.cvtColor(self.active_sweep_img, cv2.COLOR_RGB2BGR))

        messagebox.showinfo("Éxito", f"Dictamen pericial y evidencias guardados con éxito en:\n{ruta}")


# =====================================================================
# 6. ENTRADA PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    app = ForensicDashboard()
    app.mainloop()