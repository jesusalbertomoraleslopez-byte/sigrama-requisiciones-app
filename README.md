# Sistema de Control y Seguimiento de Requisiciones de Compra
## Industria SIGRAMA S.A. de C.V.

Aplicación web modular en **Streamlit** diseñada para el control, autorización y trazabilidad integral de requisiciones de compra en planta industrial, cumpliendo con los estándares de identidad corporativa de SIGRAMA y requerimientos de auditoría y revisión fiscal (SAT) en México.

---

### 🚀 Características Principales

1. **Flujo Paso a Paso Asistido:**
   - **Carga de Requisición Original (PDF):** Extracción automatizada mediante **PyMuPDF** (`pymupdf`/`fitz`) calibrada con el formato de reportes de SIGRAMA (Folio `REQ-XXXXX`, Fecha, Usuario solicitante, Departamento, Concepto y Observaciones). Permite además seleccionar directamente muestras de `Q:\002 - Requisiciones`.
   - **Formulario Inteligente:** Validación de datos contra catálogos estándar de la industria y específicos de SIGRAMA (Áreas de impacto: *Materiales, Mano de Obra, Supervisión, Gastos Generales, Herramientas, Maquinaria*).
   - **Carga Múltiple de Cotizaciones:** Cargador interactivo para adjuntar propuestas de proveedores en PDF, capturando montos, monedas, tiempos de entrega y selección de propuesta recomendada.
   - **Generación Instantánea de Correo (.eml):**
     - Asunto normativo estricto: `REQ XXXXX - Descripción Breve - Fecha - Área`
     - **Para (To):** `Lorena Hernandez Cuellar <lhernandez@sigrama.com.mx>`
     - **Con copia (Cc):**
       - `Bryan Alejandro Flores Mancinas <bryan.mancinas@sigrama.com.mx>`
       - `Cruz Eduardo Carreon Rios <cruz.carreon@sigrama.com.mx>`
       - `jose.fernandez@sigrama.com.mx`
       - `Luis Alfredo Quintana Palma <luis.quintana@sigrama.com.mx>`
       - `Jesus Alberto Morales Lopez <jesus.morales@sigrama.com.mx>`
     - Cuerpo ejecutivo en HTML con tabla comparativa y adjuntos binarios (PDFs de requisición y cotizaciones) incrustados de forma nativa en el archivo `.eml`.
   - **Control de Orden de Compra (PO):** Asociación de folio de PO, fecha, monto adjudicado, proveedor y carga de archivo probatorio (PDF o EML) para cerrar el ciclo de control.

2. **Auditoría y Trazabilidad en México (SAT / Corporativo):**
   - Relación estricta: `1 Requisición -> N Cotizaciones -> 1 Solicitud EML -> 1 Orden de Compra PO`.
   - Repositorio estructurado físico en disco local bajo la ruta:
     `data/requisiciones/REQ_XXXXX/`
   - Registro de sellos de tiempo, usuarios y firmas digitales.

3. **Panel de Control (Dashboard):**
   - Tablero visual tipo **Kanban (Estilo Odoo)** con 4 estados operativos:
     - `⏳ En Espera de Cotización`
     - `📋 Pendiente de Autorización`
     - `✅ PO Generada`
     - `📁 Archivado Histórico`
   - Tarjetas de KPIs ejecutivos con montos acumulados.
   - Filtros avanzados por Área de Impacto y buscador en tiempo real.
   - **Expediente Permanente:** Consulta y descarga con 1 solo clic de cualquier PDF o correo generado en el pasado.

4. **Módulo de Mantenimiento y Respaldos (Restringido):**
   - Acceso con PIN (`sigrama2026`).
   - Gestión y edición de catálogos base (`BD_Catalogos.xlsx`).
   - **Borrado Masivo:** Selección mediante casillas de verificación para eliminar registros y sus carpetas asociadas sin dejar archivos huérfanos.
   - **Limpieza Avanzada:** Vaciado de registros operativos preservando catálogos.
   - **Respaldo Integral (.zip):** Genera y descarga un archivo comprimido con todas las bases de datos de Excel y el repositorio completo de archivos.

---

### 📁 Estructura del Proyecto

```
sigrama_requisiciones_app/
├── app.py                      # Router principal y UI con identidad SIGRAMA
├── config.py                   # Catálogos, destinatarios oficiales (To / Cc) y rutas
├── database.py                 # Persistencia Excel (.xlsx) atómica con Pandas y openpyxl
├── pdf_parser.py               # Extractor PyMuPDF calibrado con reportes reales de planta
├── email_generator.py          # Generador de correos RFC 822 (.eml) multipart con PDFs embebidos
├── requirements.txt            # Dependencias
├── run_app.bat                 # Lanzador para Windows de un solo clic
├── brand/                      # Logotipo corporativo oficial de SIGRAMA y favicon
├── modules/
│   ├── requisition_wizard.py   # Fase 1: Carga, formulario, cotizaciones y .eml
│   ├── po_control.py           # Fase 1 (Cierre): Vinculación y cierre de PO
│   ├── dashboard.py            # Fase 3: KPIs, Kanban Odoo, filtros y expedientes
│   └── admin_backup.py         # Fase 4: Catálogos, borrado con checkboxes y respaldo .zip
└── data/                       # Base de datos y almacenamiento persistente local
    ├── BD_Requisiciones.xlsx
    ├── BD_Cotizaciones.xlsx
    ├── BD_Catalogos.xlsx
    └── requisiciones/
        └── REQ_XXXXX/
```

---

### 💻 Cómo Ejecutar la Aplicación

1. **Vía Archivo por Lotes (Recomendado):**
   Hacer doble clic en `run_app.bat`.

2. **Vía Terminal (PowerShell o CMD):**
   ```powershell
   cd C:\Users\albertol\.gemini\antigravity\scratch\sigrama_requisiciones_app
   & "C:\Users\albertol\.gemini\antigravity\scratch\test_venv\Scripts\python.exe" -m streamlit run app.py
   ```
