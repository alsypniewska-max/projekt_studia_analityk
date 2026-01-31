import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                             QMenu, QFileDialog, QTableWidget, QTableWidgetItem, QDialog, QLabel)
import pandas as pd

current_file_path = None
def import_csv():
    """
    Wybór pliku CSV i załadowanie (np. pandas).
    """
    global current_file_path
    file_path, _ = QFileDialog.getOpenFileName(
        parent=None,
        caption="Wybierz plik CSV",
        directory="/Users/ola/Documents/GitHub/projekt_studia_analityk",  # Aktualny katalog
        filter="CSV files (*.csv);;All files (*)"
    )

    if file_path:  # Jeśli użytkownik wybrał plik
        # Tutaj zaimplementuj ładowanie, np.:
        # import pandas as pd
        # df = pd.read_csv(file_path)
        # print(f"Załadowano: {file_path}")
        tabela = pd.read_csv(file_path)
        current_file_path = file_path
        print(f"Wybrano plik CSV: {file_path}")  # Tymczasowy print
    else:
        print("Anulowano wybór pliku")

def import_sql():
    """
    Pusta funkcja do importu z bazy SQL.
    Zaimplementuj np. sqlite3.connect() i pd.read_sql().
    """
    pass  # Dodaj tu kod importu SQL


def podglad_danych():
    if not current_file_path:
        print("Najpierw wczytaj plik CSV")
        return

    dialog = QDialog()
    dialog.setWindowTitle("Podgląd danych")
    dialog.resize(800, 500)  # Większe okno na tabelę

    layout = QVBoxLayout(dialog)

    info_label = QLabel(f"Plik: {current_file_path}")
    layout.addWidget(info_label)

    table = QTableWidget()
    try:
        df = pd.read_csv(current_file_path)
        nrows = min(20, len(df))  # Pokazuj max 20 wierszy
        table.setRowCount(nrows)
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())

        # Wypełnij danymi (pełna tabela)
        for row in range(nrows):
            for col in range(len(df.columns)):
                value = str(df.iloc[row, col])
                item = QTableWidgetItem(value)
                table.setItem(row, col, item)

        table.resizeColumnsToContents()
        table.setAlternatingRowColors(True)  # Ładniejszy widok
    except Exception as e:
        print(f"Błąd: {e}")
        table.setColumnCount(1)
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Błąd ładowania"))

    layout.addWidget(table)
    dialog.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wczytaj dane")
        self.setFixedSize(300, 150)

        # Central widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Przycisk z menu
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        menu = QMenu(self)
        menu.addAction("Import z CSV", import_csv)
        menu.addAction("Import z bazy SQL", import_sql)
        self.btn_wczytaj.setMenu(menu)
        layout.addWidget(self.btn_wczytaj)

        # Nowy przycisk Podgląd danych
        self.btn_podglad = QPushButton("Podgląd danych")
        self.btn_podglad.clicked.connect(podglad_danych)
        layout.addWidget(self.btn_podglad)

# Uruchomienie aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
