import sys
import random

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QHBoxLayout, \
    QComboBox
from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap, QTransform

'''
Epics:
- Custom uploaded player sprite
- Debug/Dev mode - showing hidden dificulties, collision boxes etc.
'''
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
        self.options_screen.change_resolution.connect(self.change_res)

    def start_new_game(self):
        self.stacked_widget.setCurrentIndex(1)
        self.game.setFocus()

    def open_options(self):
        self.stacked_widget.setCurrentIndex(2)

    def back_to_menu(self):
        self.stacked_widget.setCurrentIndex(0)

    def change_res(self, text):
        if text == "Fullscreen":
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.showFullScreen()
        else:
            self.showNormal()
            resolution = text.split("x")
            width = int(resolution[0])
            height = int(resolution[1])
            self.setFixedSize(width, height)

class Lane:
    def __init__(self, lane_type, y_pos, objects=None, tiles=None):
        self.lane_type = lane_type
        self.y_pos = y_pos
        self.objects = objects if objects is not None else []
        self.tiles = tiles if tiles is not None else []

class Object:
    def __init__(self, obj_type,sprite, x_pos, y_pos, speed):
        self.obj_type = obj_type
        self.sprite = sprite
        self.goesRight = random.choice([True, False])
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.speed = speed

class Game(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tile_size = 9
        self.player_x = 4
        self.player_y = 14

        self.lanes = []
        self.cars = []

        self.player_sprite = QPixmap('sprites/chicken_back.png')
        self.car_sprite_left = QPixmap('sprites/car.png')
        self.grass_sprites = []
        for i in range(1):
            self.grass_sprites.append(QPixmap(f'sprites/grass{i}.png'))
        self.transform = QTransform().scale(-1, 1)
        self.car_sprite_right = self.car_sprite_left.transformed(self.transform)

        self.generate_first_lanes()
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game_state)
        self.game_timer.start(30)

    def generate_first_lanes(self):
        for y in [15, 14]:
            grass_tiles = []
            for _ in range(9):
                grass_tiles.append(random.choice(self.grass_sprites))
            self.lanes.append(Lane("grass", y, None, grass_tiles))
        lane_types = ["road", "river", "grass"]

        for i in range(13, -1, -1):
            lane_type = random.choice(lane_types)
            if lane_type == "road":
                lane_speed = random.uniform(0.03, 0.08)
                lane_direction = random.choice([True, False])
                if lane_direction:
                    current_sprite = self.car_sprite_right
                else:
                    current_sprite = self.car_sprite_left
                lane_objects = [
                    Object("car", current_sprite, 1, i, lane_speed),
                    Object("car", current_sprite, 5, i, lane_speed),
                    Object("car", current_sprite, 9, i, lane_speed)
                ]

                for obj in lane_objects:
                    obj.goesRight = lane_direction

                self.lanes.append(Lane(lane_type, i, lane_objects))
            elif lane_type == "grass":
                grass_tiles = []
                for _ in range(9):
                    grass_tiles.append(random.choice(self.grass_sprites))
                self.lanes.append(Lane(lane_type, i, None, grass_tiles))
            elif lane_type == "river":
                self.lanes.append(Lane(lane_type, 0))

            self.lanes = [lane for lane in self.lanes if lane.y_pos <= 15]


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        window_width = self.width()
        window_height = self.height()

        game_ratio = 360 / 640
        window_ratio = window_width / window_height

        if window_ratio > game_ratio:
            game_height = window_height
            game_width = int(game_height * game_ratio)
        else:
            game_width = window_width
            game_height = int(game_width / game_ratio)

        x_offset = (window_width - game_width) // 2
        y_offset = (window_height - game_height) // 2

        painter.fillRect(x_offset, y_offset, game_width, game_height, QColor(40, 40, 40))

        cell_size = game_width / self.tile_size

        for lane in self.lanes:
            if lane.lane_type == "grass":
                for tile_index in range(9):
                    tile_x = x_offset + int(tile_index * cell_size)
                    tile_y = y_offset + int(lane.y_pos * cell_size)
                    painter.drawPixmap(
                        tile_x,
                        tile_y,
                        int(cell_size),
                        int(cell_size),
                        lane.tiles[tile_index]
                    )
            elif lane.lane_type == "road":
                painter.fillRect(x_offset, int(y_offset + lane.y_pos * cell_size), game_width, int(cell_size),
                                 QColor(127, 127, 127))
            elif lane.lane_type == "river":
                painter.fillRect(x_offset, int(y_offset + lane.y_pos * cell_size), game_width, int(cell_size),
                                 QColor(0, 162, 232))

            for obj in lane.objects:
                obj_pixel_x = x_offset + int(obj.x_pos * cell_size)
                obj_pixel_y = y_offset + int(lane.y_pos * cell_size)

                painter.drawPixmap(
                    obj_pixel_x,
                    obj_pixel_y,
                    int(cell_size),
                    int(cell_size),
                    obj.sprite
                )

        if self.player_x < 0:
            self.player_x = 0
        elif self.player_x > 8:
            self.player_x = 8

        if self.player_y < 0:
            self.player_y = 0
        elif self.player_y > 15:
            self.player_y = 15

        pixel_x = x_offset + int(self.player_x * cell_size)
        pixel_y = y_offset + int(self.player_y * cell_size)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPixmap(
            pixel_x,
            pixel_y,
            int(cell_size),
            int(cell_size),
            self.player_sprite
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_W:
            next_lane = None
            for lane in self.lanes:
                if lane.y_pos == (self.player_y - 1):
                    next_lane = lane
                    break
            if next_lane and next_lane.lane_type == "river":
                print("rzeka")
                #return
            if self.player_y > 8:
                self.player_y -= 1
            else:
                for lane in self.lanes:
                    lane.y_pos += 1

                lane_types = ["road", "river", "grass"]
                new_lane_type = random.choice(lane_types)

                if new_lane_type == "road":
                    lane_speed = random.uniform(0.03, 0.08)
                    lane_direction = random.choice([True, False])

                    if lane_direction:
                        current_sprite = self.car_sprite_right
                    else:
                        current_sprite = self.car_sprite_left

                    lane_objects = [
                        Object("car", current_sprite, 1, 0, lane_speed),
                        Object("car", current_sprite, 5, 0, lane_speed),
                        Object("car", current_sprite, 9, 0, lane_speed)
                    ]

                    for obj in lane_objects:
                        obj.goesRight = lane_direction

                    self.lanes.append(Lane(new_lane_type, 0, lane_objects))

                elif new_lane_type == "grass":
                    grass_tiles = []
                    for _ in range(9):
                        grass_tiles.append(random.choice(self.grass_sprites))
                    self.lanes.append(Lane(new_lane_type, 0, None, grass_tiles))

                elif new_lane_type == "river":
                    self.lanes.append(Lane(new_lane_type, 0))

            self.lanes = [lane for lane in self.lanes if lane.y_pos <= 15]

        elif event.key() == Qt.Key.Key_Down or event.key() == Qt.Key.Key_S:
            self.player_y += 1
        elif event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_A:
            self.player_x -= 1
        elif event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_D:
            self.player_x += 1
        elif event.key() == Qt.Key.Key_Escape:
            self.parentWidget().setCurrentIndex(0)

        self.update()

    def update_game_state(self):
        for lane in self.lanes:
            for obj in lane.objects:
                if obj.goesRight:
                    obj.x_pos += obj.speed
                else:
                    obj.x_pos -= obj.speed
                if abs(obj.x_pos-self.player_x) < 0.7 and lane.y_pos == self.player_y:
                    if obj.obj_type == "car":
                        print("collision")
                    if obj.obj_type == "log":
                        print("collision")

                if obj.x_pos > 10:
                    obj.x_pos = -2
                elif obj.x_pos < -2:
                    obj.x_pos = 10

        self.update()

class Options(QWidget):
    back_to_menu = pyqtSignal()
    change_resolution = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("ekran_opcji")

        self.setStyleSheet("""
            QWidget#ekran_opcji {
                background-color: #2b2b2b; 
            }

            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
                font-family: Arial;
                min-width: 250px;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }

            QComboBox {
                background-color: white;
                color: black;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                font-family: Arial;
                min-width: 230px; /* Lekko węższa niż przycisk */
                min-height: 55px;
                padding-left: 15px; /* Tekst nie przykleja się do lewej krawędzi */
            }
            /* Styl samej rozwijanej listy (opcji) */
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #bdc3c7; /* Kolor podświetlenia opcji */
                color: black;
                border-radius: 5px;
            }

            /* Tytuł */
            QLabel {
                color: white;
                font-size: 40px;
                font-weight: bold;
                font-family: Arial;
                margin-bottom: 20px; /* Odstęp od dołu */
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(25)

        title = QLabel("Options", self)

        self.res_options = QComboBox(self)
        self.res_options.addItems(["360x640", "720x1280", "1080x1920", "Fullscreen"])
        self.res_options.currentTextChanged.connect(lambda text: self.change_resolution.emit(text))

        self.back_btn = QPushButton("Back", self)
        self.back_btn.clicked.connect(lambda: self.back_to_menu.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.res_options, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.setLayout(layout)

class Menu(QWidget):
    new_game = pyqtSignal()
    load_game = pyqtSignal()
    options = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c; 
                        color: white; 
                        border-radius: 12px;
                        font-size: 20px;
                        font-weight: bold;
                        font-family: Arial;
                        min-width: 250px;
                        min-height: 55px;
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