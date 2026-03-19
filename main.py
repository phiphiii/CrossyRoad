import sys

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QHBoxLayout
from PyQt6.QtGui import QFont


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("phiphi's Crossy Road")
        self.resize(900, 900)

        main_layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()

        self.menu = Menu()
        self.game = Game()
        self.stacked_widget.addWidget(self.menu)
        self.stacked_widget.addWidget(self.game)

        self.setLayout(main_layout)
        main_layout.addWidget(self.stacked_widget)
        self.menu.new_game.connect(self.start_new_game)
    def start_new_game(self):
        self.stacked_widget.setCurrentIndex(1)
class Game(QWidget):
    def __init__(self):
        super().__init__()
        self.players = []
        self.score = 0
        self.label = QLabel("siema eniu",self)
class Menu(QWidget):
    new_game = pyqtSignal()
    load_game = pyqtSignal()
    options = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
                    QPushButton{
                        background-color: rgb(255, 255, 255); 
                        color: rgb(0, 0, 0); 
                        border-radius: 0px;
                        font-size: 18px;
                        font-weight: bold;
                        font-family: Arial;
                        width: 200px;
                        height: 60px;
                    }
                    QPushButton:hover{
                        background-color: rgb(200, 200, 200);
                    }
                """)
        menu_layout = QVBoxLayout()

        #Setting up buttons
        self.new_game_btn = QPushButton("New Game", self)
        self.load_game_btn = QPushButton("Load Save", self)
        self.option_btn = QPushButton("Options?", self)
        self.exit_btn = QPushButton("Exit", self)

        self.new_game_btn.clicked.connect(lambda: self.new_game.emit())
        self.load_game_btn.clicked.connect(lambda: self.load_game.emit())
        self.option_btn.clicked.connect(lambda: self.options.emit())
        self.exit_btn.clicked.connect(QApplication.instance().quit)


        menu_layout.addStretch()
        menu_layout.addWidget(self.new_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.load_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.option_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.exit_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addStretch()

        self.setLayout(menu_layout)

class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
def main():

    app = QApplication(sys.argv)
    ex = MainApp()
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()