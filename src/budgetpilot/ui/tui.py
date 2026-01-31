from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from datetime import datetime
from rich.text import Text

from textual.widgets import Header, Footer, DataTable, Static, Input, Label, Button
from ..services.budgets import list_open_budgets, get_budget, list_status_history, create_budget, kpis, stalled, set_status, list_closed_budgets
from ..services.attachments import list_attachments, add_attachment, delete_attachment, resolve_attachment_path
from ..services.exporter import export_budget
from ..utils.openfile import open_with_default_app
from ..config import STATUSES

from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Input, Static, Label, OptionList

STALL_YELLOW = 5   # días para aviso (amarillo)
STALL_RED = 10     # días para alerta (rojo)




def _days_since(dt_str: str) -> int:
    try:
        updated = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return max(0, (datetime.now() - updated).days)
    except Exception:
        return 0


HELP_TEXT = "Comandos: [N]N - Nuevo | [S]S - Estado | [F]F - Adjuntos | [T]T - Atascados | [R]R - Recargar | [Enter]Intro - Detalle | [Q]Q - Salir"

class DetailPanel(Static):
    """Panel derecho: detalle del presupuesto seleccionado."""
    def show_budget(self, budget: dict | None, history: list[dict] | None = None) -> None:
        if not budget:
            self.update("Selecciona un presupuesto en la tabla (↑/↓) y pulsa Enter.")
            return

        lines = [
            f"[b]ID:[/b] {budget['id']}",
            f"[b]Proveedor:[/b] {budget['vendor']}",
            f"[b]Num. Presupuesto:[/b] {budget['title']}",
            f"[b]Estado:[/b] {budget['status']}",
            f"[b]Importe:[/b] {budget.get('amount_estimated') or '-'} {budget.get('currency') or ''}",
            f"[b]Actualizado:[/b] {budget['updated_at']}",
            "",
            "[b]Histórico (últimos cambios):[/b]",
        ]
        history = history or []
        if not history:
            lines.append("  - (sin histórico)")
        else:
            for h in history[:6]:
                lines.append(f"  - {h['changed_at']}: {h.get('from_status') or '∅'} → {h['to_status']}  ({h.get('note') or ''})")

        self.update("\n".join(lines))


class BudgetPilotApp(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #left { width: 2fr; padding: 1; }
    #right { width: 1fr; padding: 1; border-left: heavy $accent; }
    #help { height: 3; padding: 0 1; }
    DataTable { height: 1fr; }
    #kpis { height: 3; padding: 0 2; background: $panel; }
    """

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("r", "reload", "Recargar"),
        ("n", "new_budget", "Nuevo"),
        ("f", "files", "Adjuntos"),
        ("enter", "view_detail", "Detalle"),
        ("s", "status", "Estado"),
        ("t", "toggle_stalled", "Atascados"),
        ("c", "toggle_closed", "Cerrados"),
    ]

    selected_id: reactive[int | None] = reactive(None)
    view_closed: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.kpi_bar = Static("", id="kpis")
        yield self.kpi_bar


        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Label("Presupuestos abiertos (no cerrados):")
                self.table = DataTable(zebra_stripes=True)
                self.table.cursor_type = "row"
                yield self.table

            self.detail = DetailPanel(id="right")
            yield self.detail

        # Footer fijo del framework (muestra bindings). Además, añadimos una ayuda propia.
        yield Static(HELP_TEXT, id="help")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_table()
        self.action_reload()
        self.table.focus()

    def _setup_table(self) -> None:
        self.table.clear(columns=True)
        self.table.add_columns("ID", "Proveedor", "Num. Presupuesto", "Estado", "Días", "€", "Actualizado")
        self.table.cursor_type = "row"
        self.table.fixed_columns = 1

    STALL_YELLOW = 5
    STALL_RED = 10

    def on_key(self, event) -> None:
        if event.key == "enter":
            try:
                if self.focused is self.table and self.selected_id is not None:
                    self.action_view_detail()
                    event.stop()
            except Exception:
                pass

    def action_reload(self) -> None:
        all_rows = list_closed_budgets() if self.view_closed else list_open_budgets()

        if self.show_stalled_only:
            rows = [r for r in all_rows if _days_since(r["updated_at"]) >= self.stall_threshold]
        else:
            rows = all_rows
        prev_id = self.selected_id

        
        # ---- KPI: calcular atascados ----
        threshold = getattr(self, "stall_threshold", 5)  # o 5 fijo
        stalled_count = sum(1 for r in all_rows if _days_since(r["updated_at"]) >= threshold)

        # KPIs base (si ya tienes kpis())
        try:
            info = kpis()
            #view_label = "Atascados" if getattr(self, "show_stalled_only", False) else "Abiertos"
            view_label = "Cerrados" if self.view_closed else ("Atascados" if self.show_stalled_only else "Abiertos")
            self.kpi_bar.update(
                f"[b]Abiertos:[/b] {info['abiertos']}   "
                f"[b]Atascados ≥{threshold}d:[/b] {stalled_count}   "
                f"[b]Aprobados:[/b] {info['aprobados']}   "
                f"[b]Pedidos:[/b] {info['pedidos']}   "
                f"[b]Facturados:[/b] {info['facturados']}   "
                f"[dim]Vista: {view_label}[/dim]"
            )
        except Exception:
            # Si aún no tienes kpis(), al menos muestra abiertos y atascados
            self.kpi_bar.update(
                f"[b]Abiertos:[/b] {len(all_rows)}   "
                f"[b]Atascados ≥{threshold}d:[/b] {stalled_count}"
            )

        # ---- aplicar filtro (si tienes toggle atascados) ----
        if getattr(self, "show_stalled_only", False):
            rows = [r for r in all_rows if _days_since(r["updated_at"]) >= threshold]
        else:
            rows = all_rows

        # ---- ahora ya pintas la tabla con "rows" ----
        self.table.clear()
        self._row_to_budget_id = []





        self.table.clear()
        self._row_to_budget_id = []

        for r in rows:
            days = _days_since(r["updated_at"])
            if days >= STALL_RED:
                days_cell = Text(str(days), style="bold red")
            elif days >= STALL_YELLOW:
                days_cell = Text(str(days), style="bold yellow")
            else:
                days_cell = Text(str(days), style="green")

            amount = r["amount_estimated"]
            amount_str = f"{amount:.2f} {r.get('currency','')}" if isinstance(amount, (int, float)) else "-"

            # Opcional: colorear también el estado si está “atascado”
            status_cell = r["status"]
            if days >= STALL_RED:
                status_cell = Text(r["status"], style="red")
            elif days >= STALL_YELLOW:
                status_cell = Text(r["status"], style="yellow")

            self.table.add_row(
                str(r["id"]),
                r["vendor"],
                r["title"],
                status_cell,
                days_cell,
                amount_str,
                r["updated_at"],
            )
            self._row_to_budget_id.append(int(r["id"]))

        if not rows:
            self.selected_id = None
            self.detail.show_budget(None)
            return

        # Mantener selección si posible
        row_index = self._row_to_budget_id.index(prev_id) if prev_id in self._row_to_budget_id else 0
        self.table.move_cursor(row=row_index, column=0)
        self.table.focus()

        self.selected_id = self._row_to_budget_id[row_index]
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        if self.selected_id is None:
            self.detail.show_budget(None)
            return
        budget = get_budget(self.selected_id)
        hist = list_status_history(self.selected_id)
        self.detail.show_budget(budget, hist)

    def on_data_table_row_highlighted(self, event) -> None:
        # En Textual 0.7.x normalmente event trae cursor_row
        row = getattr(event, "cursor_row", None)

        # Fallback si no viniera
        if row is None:
            row = getattr(self.table, "cursor_row", None)

        if row is None:
            return

        ids = getattr(self, "_row_to_budget_id", None)
        if not ids:
            return

        if 0 <= row < len(ids):
            self.selected_id = ids[row]
            self._refresh_detail()

    def action_open_selected(self) -> None:
        self._refresh_detail()

    def action_new_budget(self) -> None:
        # MVP rápido: creación mínima por consola emergente (más adelante haremos modal bonito)
        # Para Textual, haremos un "Input mode" simple.
        self.push_screen(NewBudgetScreen(on_created=self._on_budget_created))

    def _on_budget_created(self, budget_id: int) -> None:
        self.action_reload()

        key = str(budget_id)
        row_index = getattr(self, "row_index_by_id", {}).get(key)

        if row_index is not None:
            self.table.move_cursor(row=row_index, column=0)
            self.selected_id = budget_id
            self._refresh_detail()
        else:
            # Si por cualquier razón no aparece (filtro, etc.), al menos refrescamos
            self.selected_id = budget_id
            self._refresh_detail()


    def action_files(self) -> None:
        if self.selected_id is None:
            self.notify("Selecciona un presupuesto primero.", severity="warning")
            return
        self.push_screen(AttachmentsScreen(self.selected_id))

    def action_status(self) -> None:
        if self.selected_id is None:
            self.notify("Selecciona un presupuesto primero.", severity="warning")
            return

        budget = get_budget(self.selected_id)
        current_status = budget["status"] if budget else None

        self.push_screen(
            ChangeStatusScreen(self.selected_id, current_status=current_status, on_done=self._after_status_change)
        )

    def _after_status_change(self) -> None:
        self.action_reload()
        self._refresh_detail()

    def _days_since(dt_str: str) -> int:
        # dt_str en formato: "YYYY-MM-DD HH:MM:SS"
        try:
            updated = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return 0
        return max(0, (datetime.now() - updated).days)
    
    def action_toggle_stalled(self) -> None:
        self.show_stalled_only = not self.show_stalled_only
        self.action_reload()

    def action_toggle_closed(self) -> None:
        self.view_closed = not self.view_closed
        self.action_reload()

    def action_view_detail(self) -> None:
        self.notify("Abriendo detalle...", severity="information")
        if self.selected_id is None:
            self.notify("Selecciona un presupuesto primero.", severity="warning")
            return
        self.push_screen(DetailScreen(self.selected_id, on_close=self._after_status_change))
    
    
    show_stalled_only: reactive[bool] = reactive(False)
    stall_threshold: reactive[int] = reactive(5)


    



class NewBudgetScreen(Screen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 80; border: heavy $accent; padding: 1 2; }
    .row { height: auto; margin: 1 0; }
    #kpis { height: 3; padding: 0 2; background: $panel; }
    """

    def __init__(self, on_created):
        super().__init__()
        self.on_created = on_created

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("[b]Nuevo presupuesto[/b]\nRellena Num. Presupuesto y proveedor. (Importe opcional)")
            yield Label("Num. Presupuesto:")
            self.in_title = Input(placeholder="Ej: Sustitución cámaras parking")
            yield self.in_title

            yield Label("Proveedor:")
            self.in_vendor = Input(placeholder="Ej: Proveedor X")
            yield self.in_vendor

            yield Label("Importe sin IVA (opcional):")
            self.in_amount = Input(placeholder="Ej: 1250.50")
            yield self.in_amount

            with Horizontal(classes="row"):
                yield Button("Crear", id="create", variant="success")
                yield Button("Cancelar", id="cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return

        title = self.in_title.value.strip()
        vendor = self.in_vendor.value.strip()
        amount_raw = self.in_amount.value.strip()
        amount = None
        if amount_raw:
            try:
                amount = float(amount_raw.replace(",", "."))
            except ValueError:
                self.notify("Importe inválido. Usa número (ej: 1250.50)", severity="error")
                return

        try:
            budget_id = create_budget(title=title, vendor=vendor, amount_estimated=amount)
        except ValueError as e:
            self.notify(str(e), severity="error")
            return

        self.on_created(budget_id)
        self.app.pop_screen()

from textual.screen import Screen
from textual.widgets import Button

class AttachmentsScreen(Screen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 110; height: 32; border: heavy $accent; padding: 1 2; }
    #help2 { height: 2; }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("a", "add", "Adjuntar"),
        ("enter", "open", "Abrir"),
        ("d", "delete", "Borrar"),
        ("r", "reload", "Recargar"),
    ]

    def __init__(self, budget_id: int):
        super().__init__()
        self.budget_id = budget_id

    def compose(self):
        from textual.containers import Vertical
        from textual.widgets import Static, DataTable
        with Vertical(id="box"):
            yield Static(f"[b]Adjuntos del presupuesto #{self.budget_id}[/b]")
            self.table = DataTable(zebra_stripes=True)
            self.table.add_columns("ID", "Nombre original", "Tags", "Tamaño", "Fecha")
            self.table.cursor_type = "row"
            yield self.table
            yield Static("Comandos: [A]A - Adjuntar | [Enter]Enter - Abrir | [D]D - Borrar | [Esc]Esc - Volver | [R]R - Recargar", id="help2")

    def on_mount(self) -> None:
        self.action_reload()
        self.table.focus()   # 👈 importante para que Enter y el cursor funcionen bien

    def action_reload(self) -> None:
        self.table.clear()
        rows = list_attachments(self.budget_id)

        # 🔑 guardamos el orden de ids tal como lo pintamos en pantalla
        self._row_to_attachment_id = []

        for r in rows:
            size = r["size_bytes"] or 0
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.2f} MB"

            self.table.add_row(
                str(r["id"]),
                r["original_name"],
                r.get("tags") or "",
                size_str,
                r["added_at"],
            )
            self._row_to_attachment_id.append(int(r["id"]))

        if rows:
            self.table.move_cursor(row=0, column=0)
            self.table.focus()

    def _get_cell(self, row: int, col: int):
        """Devuelve el contenido de una celda usando el método disponible según versión de Textual."""
        if hasattr(self.table, "get_cell_at"):
            return self.table.get_cell_at(row, col)
        if hasattr(self.table, "get_cell"):
            return self.table.get_cell(row, col)
        if hasattr(self.table, "get_row"):
            r = self.table.get_row(row)
            return r[col] if r and len(r) > col else None
        return None

    def _selected_attachment_id(self) -> int | None:
        try:
            row = self.table.cursor_row
            if row is None:
                return None
            ids = getattr(self, "_row_to_attachment_id", None)
            if not ids:
                return None
            if row < 0 or row >= len(ids):
                return None
            return ids[row]
        except Exception:
            return None

    def action_open(self) -> None:
        att_id = self._selected_attachment_id()
        if not att_id:
            self.notify("No hay adjunto seleccionado (o no pude leer el ID).", severity="warning")
            return

        rows = list_attachments(self.budget_id)
        row = next((x for x in rows if x["id"] == att_id), None)
        if not row:
            self.notify("No encuentro el adjunto en BD.", severity="error")
            return

        path = resolve_attachment_path(row["stored_rel_path"])
        try:
            open_with_default_app(path)
        except Exception as e:
            self.notify(f"No se pudo abrir: {e}", severity="error")

    def action_delete(self) -> None:
        att_id = self._selected_attachment_id()
        if not att_id:
            self.notify("No hay adjunto seleccionado.", severity="warning")
            return

        # Buscar nombre para mostrarlo en el modal
        rows = list_attachments(self.budget_id)
        row = next((x for x in rows if x["id"] == att_id), None)
        name = row["original_name"] if row else f"ID {att_id}"

        def do_delete():
            delete_attachment(att_id)
            self.action_reload()

        # OJO: desde Screen en tu versión usamos self.app.push_screen
        self.app.push_screen(ConfirmDeleteScreen(
            message=f"¿Seguro que quieres borrar el adjunto:\n\n[b]{name}[/b]\n\n(Se eliminará el fichero y el registro)",
            on_yes=do_delete
        ))

    def action_add(self) -> None:
        self.app.push_screen(AddAttachmentScreen(self.budget_id, on_done=self.action_reload))

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_key(self, event) -> None:
    # Fallback: si Enter no dispara el binding, lo forzamos aquí
        if event.key == "enter":
            self.action_open()
            event.stop()


class AddAttachmentScreen(Screen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 90; border: heavy $accent; padding: 1 2; }
    """

    def __init__(self, budget_id: int, on_done):
        super().__init__()
        self.budget_id = budget_id
        self.on_done = on_done

    def compose(self):
        from textual.containers import Vertical, Horizontal
        from textual.widgets import Static, Label, Input, Button

        with Vertical(id="box"):
            yield Static(f"[b]Adjuntar archivo a presupuesto #{self.budget_id}[/b]\nPega la ruta completa del archivo.")
            yield Label("Ruta del archivo:")
            self.in_path = Input(placeholder=r"Ej: C:\Users\...\presupuesto.pdf")
            yield self.in_path

            yield Label("Tags (opcional):")
            self.in_tags = Input(placeholder="Ej: presupuesto, email, factura")
            yield self.in_tags

            with Horizontal():
                yield Button("Adjuntar", id="ok", variant="success")
                yield Button("Cancelar", id="cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return

        path = self.in_path.value.strip().strip('"')
        tags = self.in_tags.value.strip() or None

        try:
            add_attachment(self.budget_id, path, tags=tags)
        except Exception as e:
            self.notify(f"Error adjuntando: {e}", severity="error")
            return

        self.on_done()
        self.app.pop_screen()

class ConfirmDeleteScreen(Screen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 80; border: heavy $accent; padding: 1 2; }
    """

    def __init__(self, message: str, on_yes):
        super().__init__()
        self.message = message
        self.on_yes = on_yes

    def compose(self):
        from textual.containers import Vertical, Horizontal
        from textual.widgets import Static, Button
        with Vertical(id="box"):
            yield Static(f"[b]Confirmación[/b]\n\n{self.message}")
            with Horizontal():
                yield Button("Sí, borrar", id="yes", variant="error")
                yield Button("No", id="no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            try:
                self.on_yes()
            finally:
                self.app.pop_screen()
        else:
            self.app.pop_screen()


class ChangeStatusScreen(Screen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 90; border: heavy $accent; padding: 1 2; }
    #list { height: 12; border: solid $accent; }
    """

    
    BINDINGS = [
            ("tab", "toggle_focus", "Lista/Nota"),
            ("escape", "cancel", "Cancelar"),
        ]


    
    def __init__(self, budget_id: int, current_status: str | None, on_done):
            super().__init__()
            self.budget_id = budget_id
            self.current_status = current_status
            self.on_done = on_done


    def compose(self):
        yield Static(f"[b]Cambiar estado del presupuesto #{self.budget_id}[/b]\nSelecciona el nuevo estado y añade una nota (opcional).")
        with Vertical(id="box"):
            yield Label("Nuevo estado:")
            self.opts = OptionList(*STATUSES, id="list")
            yield self.opts

            yield Label("Nota (opcional):")
            self.in_note = Input(placeholder="Ej: Aprobado por dirección / pedido enviado / etc.")
            yield self.in_note

            with Horizontal():
                yield Button("Aplicar", id="apply", variant="success")
                yield Button("Cancelar", id="cancel", variant="error")

    
    def on_mount(self) -> None:
            self.opts.focus()
            # Preseleccionar
            if self.current_status in STATUSES:
                idx = STATUSES.index(self.current_status)
                # Compatibilidad con 0.7.x: intentamos varios nombres
                if hasattr(self.opts, "highlighted"):
                    self.opts.highlighted = idx
                elif hasattr(self.opts, "index"):
                    self.opts.index = idx

    
    def action_toggle_focus(self) -> None:
            """Alterna el foco entre la lista de estados y el campo nota."""
            focused = self.app.focused
            if focused is self.opts:
                self.in_note.focus()
            else:
                self.opts.focus()

    def action_cancel(self) -> None:
            self.app.pop_screen()



    def _get_selected_status(self) -> str | None:
        # OptionList expone selección por highlighted/selected (varía según versión)
        # Usamos un enfoque tolerante:
        try:
            # selected is an index in some versions
            idx = getattr(self.opts, "highlighted", None)
            if idx is None:
                idx = getattr(self.opts, "selected", None)
            if idx is None:
                return None
            # En algunos casos idx es un objeto; intentamos convertir
            idx = int(idx)
            return STATUSES[idx] if 0 <= idx < len(STATUSES) else None
        except Exception:
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return

        if event.button.id == "apply":
            new_status = self._get_selected_status()
            if not new_status:
                self.notify("Selecciona un estado.", severity="warning")
                return

            note = self.in_note.value.strip() or None
            self.notify(f"DEBUG nota capturada: {note!r}", severity="information")
            try:
                set_status(self.budget_id, new_status, note=note)
            except Exception as e:
                self.notify(f"Error cambiando estado: {e}", severity="error")
                return

            # refresco y cerrar
            try:
                self.on_done()
            finally:
                self.app.pop_screen()





class DetailScreen(ModalScreen):
    CSS = """
    Screen { align: center middle; }
    #box { width: 110; height: 34; border: heavy $accent; padding: 1 2; background: $panel; }
    #help { height: 2; }
    """

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("s", "status", "Estado"),
        ("f", "files", "Adjuntos"),
        ("r", "refresh", "Refrescar"),
        ("e", "export", "Exportar"),
    ]

    def __init__(self, budget_id: int, on_close=None):
        super().__init__()
        self.budget_id = budget_id
        self.on_close = on_close
        self.body = None  # se asigna en on_mount (cuando ya existe el widget real)

    def compose(self):
        # Import local para evitar problemas de scope/imports en versiones antiguas
        from textual.containers import Vertical
        from textual.widgets import Static

        with Vertical(id="box"):
            yield Static("Cargando detalle...", id="body")
            yield Static(
                "Comandos: [S]S - Estado | [F]F - Adjuntos | [R]R - Refrescar | [E]E - Exportar | [Esc]Esc - Volver",
                id="help",
            )

    def on_mount(self) -> None:
        # ⚠️ Garantiza que el widget ya está montado y existe
        self.body = self.query_one("#body", Static)
        #self.body = self.query_one("#body", expect_type=type(self.query_one("#body")))
        self._render_detail()

    def _render_detail(self) -> None:
        # Si por alguna razón body aún no existe, salimos sin romper
        if self.body is None:
            return

        budget = get_budget(self.budget_id)
        hist = list_status_history(self.budget_id)
        atts = list_attachments(self.budget_id)

        if not budget:
            self.body.update("No se encontró el presupuesto.")
            return

        amount = budget.get("amount_estimated")
        amount_str = f"{amount:.2f} {budget.get('currency') or ''}" if isinstance(amount, (int, float)) else "-"

        lines = [
            f"[b]Presupuesto #{budget['id']}[/b]",
            f"[b]Proveedor:[/b] {budget.get('vendor','')}",
            f"[b]Num. Presupuesto:[/b] {budget.get('title','')}",
            f"[b]Estado:[/b] {budget.get('status','')}",
            f"[b]Importe:[/b] {amount_str}",
            f"[b]Creado:[/b] {budget.get('created_at','')}",
            f"[b]Actualizado:[/b] {budget.get('updated_at','')}",
            f"[b]Adjuntos:[/b] {len(atts)}",
            "",
            "[b]Histórico (últimos cambios):[/b]",
        ]

        if not hist:
            lines.append("  - (sin histórico)")
        else:
            for h in hist[:14]:
                lines.append(
                    f"  - {h.get('changed_at','')}: {h.get('from_status') or '∅'} → {h.get('to_status','')} ({h.get('note') or ''})"
                )

        # ✅ Nunca None, siempre string
        self.body.update("\n".join(lines))

    def action_refresh(self) -> None:
        self._render_detail()

    def action_back(self) -> None:
        try:
            if callable(self.on_close):
                self.on_close()
        finally:
            self.app.pop_screen()

    def action_files(self) -> None:
        self.app.push_screen(AttachmentsScreen(self.budget_id))

    def action_status(self) -> None:
        budget = get_budget(self.budget_id)
        current_status = budget["status"] if budget else None

        def after():
            self._render_detail()

        self.app.push_screen(ChangeStatusScreen(self.budget_id, current_status=current_status, on_done=after))

    def action_export(self) -> None:
        try:
            export_dir = export_budget(self.budget_id)  # por defecto data/exports
            # Abrir la carpeta exportada en Windows (Explorer) usando app por defecto
            try:
                open_with_default_app(export_dir)
            except Exception:
                pass
            self.notify(f"Exportado en: {export_dir}", severity="information")
        except Exception as e:
            self.notify(f"Error exportando: {e}", severity="error")