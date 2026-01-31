import pandas as pd
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget


def wczytaj_dane():


    pass  # Placeholder - dodaj tu swoją implementację

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wczytaj dane")
        self.setFixedSize(300, 150)

        # Central widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Przycisk
        self.btn_wczytaj = QPushButton("Wczytaj dane")
        self.btn_wczytaj.clicked.connect(wczytaj_dane)
        layout.addWidget(self.btn_wczytaj)

# Uruchomienie aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
