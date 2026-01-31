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
    """
    Wybór pliku CSV i załadowanie (np. pandas).
    """
    global current_file_path, current_df
    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Wybierz plik CSV",
        directory="/Users/ola/Documents/GitHub/projekt_studia_analityk",  # Aktualny katalog
        filter="CSV files (*.csv);;All files (*)"
    )

    if file_path:  # Jeśli użytkownik wybrał plik
        current_file_path = file_path
        current_df = pd.read_csv(file_path)
        print(f"Wybrano plik CSV: {current_df.shape}")  # Tymczasowy print
    else:
        print("Anulowano wybór pliku")

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Dodaj tu kod importu SQL


def zastosuj_filtry(df, widgets):
    filtered_df = df.copy()

    # Filtr wieku - BEZPIECZNIE
    if widgets.chk_wiek.isChecked():
        col_wiek = df.get('Wiek', pd.Series(0.0, index=df.index))  # PRAWIDŁOWY INDEX!
        filtered_df = filtered_df[(col_wiek >= widgets.spin_wiek_min.value()) &
                                  (col_wiek <= widgets.spin_wiek_max.value())]

    # Filtr płeć - BEZPIECZNIE
    if widgets.chk_plc.isChecked() and widgets.combo_plc.currentText():
        col_plc = df.get('Płeć', pd.Series("", index=df.index))  # PRAWIDŁOWY INDEX!
        filtered_df = filtered_df[col_plc == widgets.combo_plc.currentText()]

    # Filtr ciśnienie - BEZPIECZNIE
    if widgets.chk_cisn.isChecked():
        col_skur = df.get('Ciśnienie skurczowe', pd.Series(0.0, index=df.index))
        col_rozk = df.get('Ciśnienie rozkurczowe', pd.Series(0.0, index=df.index))
        filtered_df = filtered_df[
            (col_skur >= widgets.spin_skur_min.value()) &
            (col_skur <= widgets.spin_skur_max.value()) &
            (col_rozk >= widgets.spin_rozk_min.value()) &
            (col_rozk <= widgets.spin_rozk_max.value())
            ]

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

        # LEWA 350px: przyciski + filtry
        left_widget = QWidget()
        left_widget.setFixedWidth(350)  # DOKŁADNIE 350px!
        left_layout = QVBoxLayout(left_widget)

        # Przyciski
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)
        menu.addAction("Import z CSV", import_csv)
        menu.addAction("Import z bazy SQL", import_sql)
        self.btn_wczytaj.setMenu(menu)
        left_layout.addWidget(self.btn_wczytaj)

        self.btn_podglad = QPushButton("Podgląd danych")
        self.btn_podglad.clicked.connect(self.update_table)
        left_layout.addWidget(self.btn_podglad)

        # KOMP AKT FILTROWANIE
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        group_filter = QGroupBox("Filtry")
        form_layout = QFormLayout(group_filter)
        form_layout.setContentsMargins(5, 5, 5, 5)

        # Wiek
        h_wiek = QHBoxLayout()
        self.chk_wiek = QCheckBox("Wiek")
        self.spin_wiek_min = QSpinBox();
        self.spin_wiek_min.setRange(0, 150);
        self.spin_wiek_min.setMaximumWidth(55)
        self.spin_wiek_max = QSpinBox();
        self.spin_wiek_max.setRange(0, 150);
        self.spin_wiek_max.setMaximumWidth(55)
        h_wiek.addWidget(self.chk_wiek);
        h_wiek.addWidget(QLabel("od"));
        h_wiek.addWidget(self.spin_wiek_min)
        h_wiek.addWidget(QLabel("-"));
        h_wiek.addWidget(self.spin_wiek_max)
        form_layout.addRow(h_wiek)

        # Płeć
        h_plc = QHBoxLayout()
        self.chk_plc = QCheckBox("Płeć")
        self.combo_plc = QComboBox();
        self.combo_plc.addItems(["", "K", "M"]);
        self.combo_plc.setMaximumWidth(55)
        h_plc.addWidget(self.chk_plc);
        h_plc.addWidget(self.combo_plc)
        form_layout.addRow(h_plc)

        # Ciśnienie
        h_cisn1 = QHBoxLayout()
        self.chk_cisn = QCheckBox("Ciśnienie")
        self.spin_skur_min = QSpinBox();
        self.spin_skur_min.setRange(50, 250);
        self.spin_skur_min.setMaximumWidth(45)
        self.spin_skur_max = QSpinBox();
        self.spin_skur_max.setRange(50, 250);
        self.spin_skur_max.setMaximumWidth(45)
        h_cisn1.addWidget(self.chk_cisn);
        h_cisn1.addWidget(QLabel("skurcz"));
        h_cisn1.addWidget(self.spin_skur_min)
        h_cisn1.addWidget(QLabel("-"));
        h_cisn1.addWidget(self.spin_skur_max)
        form_layout.addRow(h_cisn1)

        h_cisn2 = QHBoxLayout()
        self.spin_rozk_min = QSpinBox();
        self.spin_rozk_min.setRange(30, 150);
        self.spin_rozk_min.setMaximumWidth(45)
        self.spin_rozk_max = QSpinBox();
        self.spin_rozk_max.setRange(30, 150);
        self.spin_rozk_max.setMaximumWidth(45)
        h_cisn2.addStretch();
        h_cisn2.addWidget(QLabel("rozk"));
        h_cisn2.addWidget(self.spin_rozk_min)
        h_cisn2.addWidget(QLabel("-"));
        h_cisn2.addWidget(self.spin_rozk_max)
        form_layout.addRow(h_cisn2)

        filter_layout.addWidget(group_filter)
        scroll.setWidget(filter_widget)
        left_layout.addWidget(scroll)

        main_layout.addWidget(left_widget, stretch=0)

        # PRAWY: Tabela
        self.table = QTableWidget()
        main_layout.addWidget(self.table, stretch=1)

    def update_table(self):
        global current_df
        if current_df is None:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Brak danych"])
            self.table.setItem(0, 0, QTableWidgetItem("Najpierw wczytaj CSV"))
            return

        try:
            display_df = zastosuj_filtry(current_df, self)  # Używa poprawionej wersji
            print(f"✅ Filtry OK: {len(current_df)} → {len(display_df)} wierszy")
        except Exception as e:
            print(f"⚠️ Błąd filtra: {e} - pokazuję surowe dane")
            display_df = current_df

        # Wypełnij tabelę
        nrows = min(50, len(display_df))
        self.table.setRowCount(nrows)
        self.table.setColumnCount(len(display_df.columns))
        self.table.setHorizontalHeaderLabels(display_df.columns.tolist())

        for row in range(nrows):
            for col in range(len(display_df.columns)):
                value = str(display_df.iloc[row, col])
                item = QTableWidgetItem(value)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        self.table.setAlternatingRowColors(True)
        print(f"📊 Pokazano {nrows}/{len(display_df)} wierszy, kolumny: {list(display_df.columns)}")

    # Uruchomienie aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
