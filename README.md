# BudgetPilot 🧾🚀
**Gestión de presupuestos en terminal (TUI) con SQLite y exportación completa**

BudgetPilot es una aplicación TUI (Textual User Interface) que permite gestionar presupuestos, registrar cambios de estado con notas, adjuntar documentos y exportar informes listos para auditoría.

Pensado para entornos operativos donde se necesita **trazabilidad**, **agilidad** y **portabilidad**, todo desde la terminal.

---

<p align="left">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
  <img alt="Language: Python" src="https://img.shields.io/badge/Python-3.10+-blue">
  <img alt="TUI: Textual" src="https://img.shields.io/badge/Textual-TUI-purple">
  <img alt="Database: SQLite" src="https://img.shields.io/badge/SQLite-local-lightgrey">
</p>

---

## 📸 Capturas de Pantalla

### Pantalla principal
<p align="center">
  <!-- Sustituir por: <img src="docs/main.png" width="750"> -->
  <img src="https://github.com/user-attachments/assets/14091917-3978-4e6c-8f47-07988e5a390a" width="750">
</p>

### Detalle del presupuesto
<p align="center">
  <!-- Sustituir por: <img src="docs/detail.png" width="750"> -->
  <img src="https://github.com/user-attachments/assets/3e011ca1-b4f1-4053-b47f-99b171d95367" width="750">
</p>

### Selección de estado y notas adicionales
<p align="center">
  <!-- Sustituir por: <img src="docs/detail.png" width="750"> -->
  <img src="https://github.com/user-attachments/assets/f950fa95-0817-4331-b258-0b0b629127ce" width="750">
</p>
---

## ✨ Características

- 📋 **Listado de presupuestos** abiertos y cerrados  
- 🔁 **Cambio de estado** con **nota opcional** (queda registrada en el histórico)  
- 📎 **Gestión de adjuntos**: añadir, abrir, borrar  
- 🕒 **Vista de atascados** según días sin actualizar  
- 📦 **Exportación completa**:  
  - `resumen.txt`  
  - Copia de todos los adjuntos  
- 🧭 Navegación fluida totalmente con teclado  
- 🗄️ Datos almacenados de forma local en **SQLite**

---

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/afgsanchez/BudgetPilot.git
```
```bash
cd BudgetPilot
```
### 2. Crear entorno virtual
```bash
python -m venv .venv
```
### Windows
```bash
.venv\Scripts\activate
```
### Linux/macOS
```bash
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### ▶️ Uso
Ejecuta la aplicación desde la raíz del proyecto:
```bash
python src/budgetpilot/app.py
```
(Dependiendo de tu configuración, también puede ser:)
```bash
python -m budgetpilot
```
⌨️ Atajos del teclado (TUI)

Pantalla principal:

N → Nuevo presupuesto

S → Cambiar estado

F → Adjuntos

T → Ver atascados

C → Ver cerrados

R → Recargar

Enter → Ver detalle

Q → Salir


En el detalle:

S → Cambiar estado

F → Adjuntos

E → Exportar

R → Refrescar

Esc → Volver



📦 Exportación
Al exportar un presupuesto se genera una carpeta con estructura:
```bash
exports/BP_000123_20260201_153108_Vendor_Titulo/
├── resumen.txt
└── attachments/
    ├── archivo1.pdf 
    ├── archivo2.png
    └── ...
```

resumen.txt incluye:

Datos clave

Histórico de estados (con notas)

Lista detallada de adjuntos



🗂️ Estructura del Proyecto
```bash
src/budgetpilot/
├── ui/
│   └── tui.py             # Interfaz TUI (Textual)
├── services/
│   ├── budgets.py         # Lógica de presupuestos + histórico
│   ├── attachments.py     # Adjuntos
│   └── exporter.py        # Exportación TXT + archivos
├── utils/
│   ├── openfile.py
│   ├── paths.py
│   └── hashing.py
├── config.py              # Configuración general
├── db.py                  # Conexión SQLite
└── app.py                 # Punto de entrada
data/
├── budgetpilot.db         # Base de datos
├── attachments/           # Archivos ligados a presupuestos
└── exports/               # Exportaciones generadas
```

💡 Estados definidos
Los estados disponibles están en config.py
y pueden personalizarse fácilmente modificando la lista STATUSES.

🛣️ Roadmap (próximas mejoras):
```bash
   Búsqueda por proveedor, número o notas
   Exportación a CSV / Excel
   Campos adicionales (prioridad, departamento, fecha objetivo)
   Módulo CLI para automatizar tareas
   Tests unitarios
   ```


🤝 Contribuir
¡Las contribuciones son bienvenidas!
```bash
Haz un fork
Crea tu rama: git checkout -b feature/nueva-funcion
Commit: git commit -m "Añadir nueva función"
Push: git push origin feature/nueva-funcion
Abre un Pull Request
```

📄 Licencia
Este proyecto está bajo licencia MIT.
Puedes consultarla en el archivo LICENSE.

🙌 Agradecimientos

Hecho con ❤ utilizando Textual
y diseñado para un uso real en operaciones y mantenimiento.
