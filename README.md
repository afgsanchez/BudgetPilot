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
cd BudgetPilot
```
### 2. Crear entorno virtual
python -m venv .venv
### Windows
.venv\Scripts\activate
### Linux/macOS
source .venv/bin/activate

### 3. Instalar dependencias
pip install -r requirements.txt

### ▶️ Uso
Ejecuta la aplicación desde la raíz del proyecto:
python src/budgetpilot/app.py
