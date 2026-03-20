import sys

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QHBoxLayout
from PyQt6.QtGui import QFont, QPainter, QColor, QIcon, QPixmap


class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("phiphi's Crossy Road")
        #self.size(360, 640)
        self.setFixedSize(360, 640)

        main_layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()

        self.menu = Menu()
        self.game = Game()
        self.options_screen = Options()
        self.stacked_widget.addWidget(self.menu)
        self.stacked_widget.addWidget(self.game)
        self.stacked_widget.addWidget(self.options_screen)

        self.setLayout(main_layout)
        main_layout.addWidget(self.stacked_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.menu.new_game.connect(self.start_new_game)
        self.menu.options.connect(self.open_options)
        self.options_screen.back_to_menu.connect(self.back_to_menu)

    def start_new_game(self):
        self.stacked_widget.setCurrentIndex(1)
        self.game.setFocus()

    def open_options(self):
        self.stacked_widget.setCurrentIndex(2)

    def back_to_menu(self):
        self.stacked_widget.setCurrentIndex(0)

class Player:
    def __init__(self, name):
        self.name = name
        self.score = 0
class Game(QWidget):
    def __init__(self):
        super().__init__()
        self.tile_size = 9
        self.player_x = 4
        self.player_y = 14

        self.player_sprite = QPixmap('sprites/amogus.png')
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))



        window_width = self.width()
        window_height = self.height()
        if window_width / window_height > self.width() / self.height():
            game_height = window_height
            game_width = int(game_height * self.width() / self.height())
        else:
            game_width = window_width
            game_height = int(game_width * self.height() / self.width())
        x_offset = (window_width - game_width) // 2
        y_offset = (window_height - game_height) // 2

        painter.fillRect(x_offset, y_offset, game_width, game_height, QColor(40, 40, 40))

        pixel_x = x_offset + int(self.player_x * game_width / self.tile_size)
        pixel_y = y_offset + int(self.player_y * game_width / self.tile_size)

        #painter.drawRect(pixel_x, pixel_y, int(game_width / self.tile_size), int(game_width / self.tile_size))
        #painter.setBrush(QColor(255, 0, 255))painter.setPen(Qt.PenStyle.NoPen)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPixmap(
            pixel_x,
            pixel_y,
            int(game_width / self.tile_size),
            int(game_width / self.tile_size),
            self.player_sprite
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_W:
            self.player_y -= 1
        elif event.key() == Qt.Key.Key_Down or event.key() == Qt.Key.Key_S:
            self.player_y += 1
        elif event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_A:
            self.player_x -= 1
        elif event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_D:
            self.player_x += 1
        elif event.key() == Qt.Key.Key_Escape:
            self.parentWidget().setCurrentIndex(0)
        self.update()


class Options(QWidget):
    back_to_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        title = QLabel("Options", self)
        title.setStyleSheet("color: white; font-size: 24px;")
        self.back_btn = QPushButton("Back", self)
        self.back_btn.clicked.connect(lambda: self.back_to_menu.emit())

        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


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
                    QLabel{
                        color: rgb(255, 255, 255);
                        font-family: Arial;
                        font-size: 32px;
                        font-weight: bold;
                    }
                    QLabel#author{
                        font-size: 16px;
                        font-weight: normal;
                        padding-bottom: 20px;
                    }
                """)
        menu_layout = QVBoxLayout()

        #Title
        title = QLabel("Crossy Road", self)
        author = QLabel("Filip Pietrzak 198275", self)
        author.setObjectName("author")

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
        menu_layout.addWidget(title,alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(author,alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.new_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.load_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.option_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.exit_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addStretch()

        self.setLayout(menu_layout)


def main():

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('sprites/amogus.png'))
    ex = MainApp()
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
