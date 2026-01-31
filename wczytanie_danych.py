import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMenu, QFileDialog,
                             QTableWidget, QTableWidgetItem, QLabel, QSpinBox, QCheckBox, QDoubleSpinBox,
                             QGroupBox, QFormLayout, QScrollArea, QComboBox)

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

        # WAŻNE: dokończenie layoutu lewej kolumny
        left_layout.addStretch()
        main_layout.addWidget(left_widget, stretch=0)

        # PRAWY: Tabela
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table, stretch=1)

    def import_csv_and_refresh(self):
        import_csv()
        self.create_dynamic_filters()
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
