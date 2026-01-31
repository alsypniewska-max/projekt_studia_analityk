import sys
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QMenu, QScrollArea, QTableWidget, QTableWidgetItem,
    QLabel, QCheckBox, QComboBox, QSpinBox, QStackedWidget,
    QFileDialog
)


from PyQt6.QtCore import Qt
import pandas as pd
import numpy as np

current_file_path = None
current_df = None

def parse_pressure(value):
    """Parsuje ciśnienie np. '100/40' -> (100, 40), None jeśli brak."""
    if pd.isna(value):
        return None, None
    match = re.match(r'(\d+)/(\d+)', str(value))
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)

def import_csv():
    global current_file_path, current_df

    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Wybierz plik CSV",
        directory="/Users/ola/Documents/GitHub/projekt_studia_analityk",
        filter="CSV files (*.csv);;All files (*)"
    )
    if not file_path:
        print("Anulowano wybór pliku")
        return

    current_file_path = file_path
    current_df = pd.read_csv(file_path)
    print(f"Wybrano plik CSV: {current_df.shape}")

    # WAŻNE: nie wywołuj tu window.create_dynamic_filters()
    # Filtry odświeżymy z poziomu MainWindow (poniżej).

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Dodaj tu kod importu SQL

def zastosuj_filtry(df, widgets):
    filtered_df = df.copy()

    # Jeśli filtry jeszcze nie wygenerowane
    if not hasattr(widgets, "filter_widgets") or not widgets.filter_widgets:
        return filtered_df

    for col, controls in widgets.filter_widgets.items():
        if not controls["chk"].isChecked():
            continue

        # Liczbowe: min/max
        if "min" in controls and "max" in controls:
            # bierz dane z filtered_df (po wcześniejszych filtrach) i konwertuj do liczb
            col_data = pd.to_numeric(filtered_df[col], errors="coerce")

            vmin = controls["min"].value()
            vmax = controls["max"].value()

            mask = col_data.between(vmin, vmax, inclusive="both")
            filtered_df = filtered_df[mask]

            print(f"Filtr '{col}': {vmin} - {vmax}")

        # Tekstowe: == wybrana wartość
        elif "combo" in controls:
            val = controls["combo"].currentText()
            if val == "":
                continue

            # porównuj jako string, żeby było stabilnie
            mask = filtered_df[col].astype(str) == str(val)
            filtered_df = filtered_df[mask]

            print(f"Filtr '{col}': = '{val}'")

    return filtered_df

def podglad_danych():
    if current_df is None:
        print("Najpierw wczytaj plik")
        return

    dialog = QDialog()
    dialog.setWindowTitle("Podgląd danych")
    dialog.resize(900, 600)

    layout = QVBoxLayout(dialog)

    # Zastosuj filtry jeśli włączone
    display_df = zastosuj_filtry(current_df)

    info_label = QLabel(f"Plik: {current_file_path} | Wiersze: {len(display_df)}")
    layout.addWidget(info_label)

    table = QTableWidget()
    nrows = min(50, len(display_df))
    table.setRowCount(nrows)
    table.setColumnCount(len(display_df.columns))
    table.setHorizontalHeaderLabels(display_df.columns.tolist())

    for row in range(nrows):
        for col in range(len(display_df.columns)):
            value = str(display_df.iloc[row, col])
            item = QTableWidgetItem(value)
            table.setItem(row, col, item)

    table.resizeColumnsToContents()
    table.setAlternatingRowColors(True)
    layout.addWidget(table)
    dialog.exec()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wczytaj dane - Filtry i podgląd")
        self.setMinimumSize(1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # LEWA KOLUMNA 350px
        left_widget = QWidget()
        left_widget.setFixedWidth(350)
        left_layout = QVBoxLayout(left_widget)

        # Przyciski górne
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)

        action_csv = menu.addAction("Import z CSV")
        action_csv.triggered.connect(self.import_csv_and_refresh)

        action_sql = menu.addAction("Import z bazy SQL")
        action_sql.triggered.connect(import_sql)

        self.btn_wczytaj.setMenu(menu)
        left_layout.addWidget(self.btn_wczytaj)

        self.btn_podglad = QPushButton("Podgląd danych")
        self.btn_podglad.clicked.connect(self.update_table)
        left_layout.addWidget(self.btn_podglad)

        # ScrollArea na dynamiczne filtry
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)

        filter_widget = QWidget()
        self.scroll_layout = QVBoxLayout(filter_widget)
        scroll.setWidget(filter_widget)
        left_layout.addWidget(scroll)

        # Miejsce na kontrolki filtrów
        self.filter_widgets = {}

        # Przycisk Filtruj i wyświetl
        self.btn_filtruj = QPushButton("Filtruj i wyświetl")
        self.btn_filtruj.clicked.connect(self.update_table)
        self.btn_filtruj.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;"
        )
        left_layout.addWidget(self.btn_filtruj)

        # Przycisk Statystyka (toggle: on/off)
        self.btn_statystyka = QPushButton("Statystyka")
        self.btn_statystyka.setCheckable(True)
        self.btn_statystyka.toggled.connect(self.toggle_stats_mode)
        self.btn_statystyka.setStyleSheet("""
            QPushButton { padding: 6px; }
            QPushButton:checked { background-color: #2196F3; color: white; font-weight: bold; }
        """)
        left_layout.addWidget(self.btn_statystyka)

        # WAŻNE: dokończenie layoutu lewej kolumny
        left_layout.addStretch()
        main_layout.addWidget(left_widget, stretch=0)

        # PRAWY: Kontener (pasek statystyk nad tabelą + stos widoków)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # Pasek statystyk (na start ukryty)
        self.stats_bar = QWidget()
        stats_bar_layout = QVBoxLayout(self.stats_bar)
        stats_bar_layout.setContentsMargins(0, 0, 0, 0)
        stats_bar_layout.setSpacing(4)

        # Rząd 1: akcje + wybór statystyk
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(8)

        self.btn_analizuj = QPushButton("Analizuj")
        self.btn_analizuj.clicked.connect(self.run_analysis)
        row1.addWidget(self.btn_analizuj)

        self.btn_dane = QPushButton("Dane")
        self.btn_dane.clicked.connect(lambda: self.view_stack.setCurrentIndex(0))
        row1.addWidget(self.btn_dane)

        self.chk_mean = QCheckBox("Średnia")
        self.chk_median = QCheckBox("Mediana")
        self.chk_min = QCheckBox("Minimum")
        self.chk_max = QCheckBox("Maximum")
        for w in (self.chk_mean, self.chk_median, self.chk_min, self.chk_max):
            w.stateChanged.connect(self.update_stats_view)

        row1.addWidget(self.chk_mean)
        row1.addWidget(self.chk_median)
        row1.addWidget(self.chk_min)
        row1.addWidget(self.chk_max)
        row1.addStretch(1)
        stats_bar_layout.addLayout(row1)

        # Rząd 2: dynamiczne checkboxy kategorii + wybór kolumny liczbowej
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(8)

        row2.addWidget(QLabel("Grupuj po:"))

        self.stats_scroll = QScrollArea()
        self.stats_scroll.setWidgetResizable(True)
        self.stats_scroll.setFixedHeight(55)

        self.stats_cat_widget = QWidget()
        self.stats_scroll_layout = QHBoxLayout(self.stats_cat_widget)
        self.stats_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_scroll_layout.setSpacing(6)
        self.stats_scroll.setWidget(self.stats_cat_widget)

        row2.addWidget(self.stats_scroll, stretch=1)

        row2.addWidget(QLabel("Wartość:"))
        self.cmb_value = QComboBox()
        self.cmb_value.currentIndexChanged.connect(self.update_stats_view)
        row2.addWidget(self.cmb_value)

        stats_bar_layout.addLayout(row2)

        self.stats_bar.setVisible(False)

        # Tabele + stos widoków
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        self.stats_table = QTableWidget()

        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.table)  # index 0: dane
        self.view_stack.addWidget(self.stats_table)  # index 1: statystyka
        self.view_stack.setCurrentIndex(0)

        # Dynamiczne checkboxy kategorii
        self.stats_cat_widgets = {}

        right_layout.addWidget(self.stats_bar)
        right_layout.addWidget(self.view_stack, stretch=1)

        main_layout.addWidget(right_widget, stretch=1)

    def import_csv_and_refresh(self):
        import_csv()
        self.create_dynamic_filters()
        self.refresh_stats_controls()
        self.update_table()

    def create_dynamic_filters(self):
        global current_df
        if current_df is None:
            return

        # Wyczyść stare filtry (usuń layouty i widgety)
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            layout = item.layout()
            widget = item.widget()

            if layout is not None:
                while layout.count():
                    sub = layout.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                layout.deleteLater()

            if widget is not None:
                widget.deleteLater()

        self.filter_widgets = {}

        for col in current_df.columns:
            chk = QCheckBox(str(col))
            chk.setChecked(False)
            chk.setMaximumWidth(140)
            chk.setMinimumWidth(140)
            chk.setToolTip(str(col))

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addWidget(chk)

            if pd.api.types.is_numeric_dtype(current_df[col]):
                s = pd.to_numeric(current_df[col], errors="coerce")
                vmin = s.min()
                vmax = s.max()
                if pd.isna(vmin): vmin = 0
                if pd.isna(vmax): vmax = 0

                spin_min = QSpinBox()
                spin_max = QSpinBox()
                spin_min.setMaximumWidth(60)
                spin_max.setMaximumWidth(60)

                spin_min.setRange(int(vmin) - 1, int(vmax) + 1)
                spin_max.setRange(int(vmin) - 1, int(vmax) + 1)
                spin_min.setValue(int(vmin))
                spin_max.setValue(int(vmax))

                row.addWidget(QLabel("od"))
                row.addWidget(spin_min)
                row.addWidget(QLabel("do"))
                row.addWidget(spin_max)

                self.filter_widgets[col] = {"chk": chk, "min": spin_min, "max": spin_max}
            else:
                combo = QComboBox()
                combo.setMinimumWidth(140)
                combo.setMaximumWidth(160)
                combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                combo.setMinimumContentsLength(8)
                combo.setToolTip(str(col))

                values = (
                    current_df[col]
                    .dropna()
                    .astype(str)
                    .value_counts()
                    .index[:20]
                    .tolist()
                )
                combo.addItem("")
                combo.addItems(values)

                row.addWidget(combo)
                self.filter_widgets[col] = {"chk": chk, "combo": combo}

            self.scroll_layout.addLayout(row)

    def update_table(self):
        global current_df
        if current_df is None:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Brak danych"])
            self.table.setItem(0, 0, QTableWidgetItem("Najpierw wczytaj CSV"))
            return

        try:
            display_df = zastosuj_filtry(current_df, self)
        except Exception as e:
            print(f"Błąd filtra: {e} - pokazuję surowe dane")
            display_df = current_df

        nrows = min(50, len(display_df))
        self.table.setRowCount(nrows)
        self.table.setColumnCount(len(display_df.columns))
        self.table.setHorizontalHeaderLabels(display_df.columns.tolist())

        for r in range(nrows):
            for c in range(len(display_df.columns)):
                self.table.setItem(r, c, QTableWidgetItem(str(display_df.iloc[r, c])))

        self.table.resizeColumnsToContents()
        self.table.setAlternatingRowColors(True)

        if self.stats_bar.isVisible():
            self.refresh_stats_controls()
            self.update_stats_view()

        if self.btn_statystyka.isChecked():
            self.refresh_stats_controls()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            l = item.layout()
            if l is not None:
                self.clear_layout(l)
                l.deleteLater()
            if w is not None:
                w.deleteLater()

    def toggle_stats_bar(self):
        visible = not self.stats_bar.isVisible()
        self.stats_bar.setVisible(visible)  # pokaż/ukryj pasek opcji [web:212]
        if visible:
            self.refresh_stats_controls()

    def refresh_stats_controls(self):
        global current_df
        if current_df is None:
            self.cmb_value.clear()
            self.clear_layout(self.stats_scroll_layout)
            self.stats_cat_widgets = {}
            return

        # Odśwież listę kolumn liczbowych do obliczeń
        self.cmb_value.blockSignals(True)
        self.cmb_value.clear()
        num_cols = [c for c in current_df.columns if pd.api.types.is_numeric_dtype(current_df[c])]
        self.cmb_value.addItems([str(c) for c in num_cols])
        self.cmb_value.blockSignals(False)

        # Odśwież checkboxy kategorii (kolumny do grupowania)
        self.clear_layout(self.stats_scroll_layout)
        self.stats_cat_widgets = {}

        cat_cols = [c for c in current_df.columns if not pd.api.types.is_numeric_dtype(current_df[c])]
        for col in cat_cols:
            chk = QCheckBox(str(col))
            chk.setChecked(False)
            chk.stateChanged.connect(self.update_stats_view)
            self.stats_scroll_layout.addWidget(chk)
            self.stats_cat_widgets[col] = chk

        self.stats_scroll_layout.addStretch(1)

    def get_selected_group_col(self):
        selected = [col for col, chk in self.stats_cat_widgets.items() if chk.isChecked()]
        return selected[0] if selected else None

    def render_df_to_table(self, df, table):
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r in range(len(df)):
            for c in range(len(df.columns)):
                table.setItem(r, c, QTableWidgetItem(str(df.iat[r, c])))
        table.resizeColumnsToContents()

    def update_stats_view(self):
        global current_df
        if current_df is None:
            return

        group_col = self.get_selected_group_col()
        value_col = self.cmb_value.currentText()
        if not group_col or not value_col:
            self.stats_table.setRowCount(0)
            self.stats_table.setColumnCount(0)
            return

        aggs = []
        if self.chk_mean.isChecked(): aggs.append("mean")
        if self.chk_median.isChecked(): aggs.append("median")
        if self.chk_min.isChecked(): aggs.append("min")
        if self.chk_max.isChecked(): aggs.append("max")
        if not aggs:
            self.stats_table.setRowCount(0)
            self.stats_table.setColumnCount(0)
            return

        # 1) bierzemy dane przefiltrowane (to co w tabeli) [web:130]
        try:
            display_df = zastosuj_filtry(current_df, self).copy()
        except Exception:
            display_df = current_df.copy()

        # 2) groupby + agg na przefiltrowanych danych, reset_index żeby mieć normalny DF [web:141]
        df = display_df[[group_col, value_col]].copy()
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

        result = (
            df.groupby(group_col, dropna=False)[value_col]
            .agg(aggs)
            .reset_index()
        )

        self.render_df_to_table(result, self.stats_table)

    def run_analysis(self):
        # Najpierw policz wynik statystyk (na przefiltrowanych danych)
        self.update_stats_view()

        # Przełącz widok na tabelę statystyk
        self.view_stack.setCurrentIndex(1)  # pokaż statystykę [web:207]

    def toggle_stats_mode(self, active: bool):
        # aktywny tryb: pokaż pasek, odśwież kontrolki, przełącz widok na statystyki
        self.stats_bar.setVisible(active)  # show/hide przez setVisible [web:161]
        if active:
            self.refresh_stats_controls()
            # nie licz od razu; dopiero po kliknięciu "Analizuj"
            self.view_stack.setCurrentIndex(1)  # statystyka [web:207]
        else:
            self.view_stack.setCurrentIndex(0)  # dane [web:207]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
