import sys
import random
import os
import json

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize, QRect, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QComboBox
from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap, QTransform, QFontDatabase, QFont, QKeyEvent


class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("phiphi's Crossy Road")
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

        self.previous_index = 0

        self.menu.new_game.connect(self.start_new_game)
        self.menu.load_game.connect(self.load_saved_game)
        self.menu.options.connect(self.open_options)
        self.options_screen.back_to_menu.connect(self.back_from_options)
        self.options_screen.change_resolution.connect(self.change_res)
        self.options_screen.god_mode_changed.connect(self.update_god_mode)
        self.options_screen.debug_mode_changed.connect(self.update_debug_mode)
        self.options_screen.river_block_changed.connect(self.update_river_block)
        self.options_screen.ai_mode_changed.connect(self.update_ai_mode)

        self.game.open_options.connect(self.open_options)
        self.game.back_to_main.connect(self.back_to_main)

    def load_saved_game(self):
        if self.game.load_game():
            self.stacked_widget.setCurrentIndex(1)
            self.game.setFocus()
    def start_new_game(self):
        self.game.reset_game()
        self.stacked_widget.setCurrentIndex(1)
        self.game.setFocus()

    def open_options(self):
        self.previous_index = self.stacked_widget.currentIndex()
        self.stacked_widget.setCurrentIndex(2)

    def back_from_options(self):
        self.stacked_widget.setCurrentIndex(self.previous_index)
        if self.previous_index == 1:
            self.game.setFocus()

    def back_to_main(self):
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

    def update_god_mode(self, state):
        self.game.god_mode = state

    def update_debug_mode(self, state):
        self.game.debug_mode = state

    def update_river_block(self, state):
        self.game.river_block = state

    def update_ai_mode(self, state):
        self.game.ai_mode = state

class Lane:
    def __init__(self, lane_type, y_pos, objects=None, tiles=None):
        self.lane_type = lane_type
        self.y_pos = y_pos
        self.objects = objects if objects is not None else []
        self.tiles = tiles if tiles is not None else []


class Object:
    def __init__(self, obj_type, sprite, x_pos, y_pos, speed):
        self.obj_type = obj_type
        self.sprite = sprite
        self.goesRight = random.choice([True, False])
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.speed = speed

    def get_hitbox(self):
        if self.obj_type == "car":
            if self.goesRight:
                return self.x_pos + 0.1, self.x_pos + 0.8
            else:
                return self.x_pos + 0.2, self.x_pos + 0.9
        elif self.obj_type == "log":
            return self.x_pos - 0.2, self.x_pos + 1.2
        elif self.obj_type == "lilypad":
            return self.x_pos + 0.1, self.x_pos + 0.9
        return self.x_pos, self.x_pos + 1.0

class Game(QWidget):
    open_options = pyqtSignal()
    back_to_main = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tile_size = 9
        self.player_x = 4
        self.player_y = 14

        self.absolute_y = 0
        self.score = 0
        self.difficulty = 0.0
        self.spawn_rate = 0.5
        self.god_mode = False
        self.debug_mode = False
        self.river_block = True
        self.ai_mode = False
        self.is_paused = False

        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self.ai_step)
        self.ai_timer.start(30)

        self.lanes = []
        self.cars = []

        self.player_sprite = QPixmap('sprites/chicken_back.png')
        self.car_sprite_left = QPixmap('sprites/car.png')
        self.water_sprite = QPixmap('sprites/tiles/water.png')
        self.road_sprite = QPixmap('sprites/tiles/road.png')
        self.log_sprite = QPixmap('sprites/log.png')
        self.tree_sprite = QPixmap('sprites/tree.png')
        self.lilypad_sprite = QPixmap('sprites/lilypad.png')
        self.grass_sprites = []

        for i in range(16):
            self.grass_sprites.append(QPixmap(f'sprites/tiles/grass/grass{i}.png'))

        self.transform = QTransform().scale(-1, 1)
        self.car_sprite_right = self.car_sprite_left.transformed(self.transform)

        self.generate_first_lanes()

        self.pause_overlay = QWidget(self)
        self.pause_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                border-radius: 12px;
                font-size: 20px;
                font-family: "Press Start 2P";
                min-width: 250px;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        pause_layout = QVBoxLayout(self.pause_overlay)
        pause_layout.setSpacing(20)

        self.resume_btn = QPushButton("Resume", self.pause_overlay)
        self.save_btn = QPushButton("Save Game", self.pause_overlay)
        self.restart_btn = QPushButton("Restart", self.pause_overlay)
        self.options_btn = QPushButton("Options", self.pause_overlay)
        self.menu_btn = QPushButton("Main Menu", self.pause_overlay)

        self.resume_btn.clicked.connect(self.toggle_pause)
        self.save_btn.clicked.connect(self.save_game)
        self.restart_btn.clicked.connect(self.reset_game)
        self.options_btn.clicked.connect(lambda: self.open_options.emit())
        self.menu_btn.clicked.connect(lambda: self.back_to_main.emit())

        pause_layout.addStretch()
        pause_layout.addWidget(self.resume_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        pause_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        pause_layout.addWidget(self.restart_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        pause_layout.addWidget(self.options_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        pause_layout.addWidget(self.menu_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        pause_layout.addStretch()

        self.pause_overlay.hide()

        self.is_dead = False

        self.game_over_overlay = QWidget(self)
        self.game_over_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
            QLabel#title {
                color: red;
                font-size: 36px;
                background: transparent;
            }
            QLabel#score {
                color: white;
                font-size: 24px;
                background: transparent;
            }
            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                border-radius: 12px;
                font-size: 20px;
                min-width: 250px;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        go_layout = QVBoxLayout(self.game_over_overlay)
        go_layout.setSpacing(20)

        self.go_title = QLabel("GAME OVER", self.game_over_overlay)
        self.go_title.setObjectName("title")
        self.go_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.go_score_label = QLabel("Score: 0", self.game_over_overlay)
        self.go_score_label.setObjectName("score")
        self.go_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.go_restart_btn = QPushButton("Restart", self.game_over_overlay)
        self.go_menu_btn = QPushButton("Main Menu", self.game_over_overlay)

        self.go_restart_btn.clicked.connect(self.reset_game)
        self.go_menu_btn.clicked.connect(lambda: self.back_to_main.emit())

        go_layout.addStretch()
        go_layout.addWidget(self.go_title, alignment=Qt.AlignmentFlag.AlignCenter)
        go_layout.addWidget(self.go_score_label, alignment=Qt.AlignmentFlag.AlignCenter)
        go_layout.addWidget(self.go_restart_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        go_layout.addWidget(self.go_menu_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        go_layout.addStretch()

        self.game_over_overlay.hide()

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game_state)
        self.game_timer.start(30)

    def resizeEvent(self, event):
        self.pause_overlay.resize(self.width(), self.height())
        self.game_over_overlay.resize(self.width(), self.height())
        super().resizeEvent(event)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.game_timer.stop()
            self.pause_overlay.show()
        else:
            self.game_timer.start(30)
            self.pause_overlay.hide()
            self.setFocus()

    def game_over(self):
        self.is_dead = True
        self.game_timer.stop()
        self.go_score_label.setText(f"Score: {self.score}")
        self.game_over_overlay.show()
        self.log_event("Player died. Game Over.")

    def reset_game(self):
        self.player_x = 4
        self.player_y = 14
        self.absolute_y = 0
        self.score = 0
        self.difficulty = 0.0
        self.spawn_rate = 0.5
        self.is_dead = False
        self.lanes = []
        self.generate_first_lanes()
        if self.is_paused:
            self.toggle_pause()
        self.game_over_overlay.hide()
        self.game_timer.start(30)
        self.update()
        self.log_event("Game started / reset.")

    def save_game(self):
        save_data = {
            "score": self.score,
            "absolute_y": self.absolute_y,
            "player_x": self.player_x,
            "player_y": self.player_y,
            "lanes": []
        }
        for lane in self.lanes:
            lane_data = {
                "lane_type": lane.lane_type,
                "y_pos": lane.y_pos,
                "objects": []
            }
            for obj in lane.objects:
                lane_data["objects"].append({
                    "obj_type": obj.obj_type,
                    "x_pos": obj.x_pos,
                    "y_pos": obj.y_pos,
                    "speed": obj.speed,
                    "goesRight": obj.goesRight
                })
            save_data["lanes"].append(lane_data)

            with open("savegame.json", "w") as f:
                json.dump(save_data, f)
            self.toggle_pause()
            self.log_event("Game saved to savegame.json")
            self.is_dead = False
            if self.is_paused:
                self.toggle_pause()
            self.game_over_overlay.hide()
            self.game_timer.start(30)
            self.update()
            self.log_event("Game loaded from savegame.json")
            return True

    def load_game(self):
        if not os.path.exists("savegame.json"):
            return False

        with open("savegame.json", "r") as f:
            save_data = json.load(f)

        self.score = save_data["score"]
        self.difficulty = self.score * 0.0001
        self.spawn_rate = min(0.5 + self.difficulty * 10, 0.95)
        self.absolute_y = save_data["absolute_y"]
        self.player_x = save_data["player_x"]
        self.player_y = save_data["player_y"]

        self.lanes = []
        for lane_data in save_data["lanes"]:
            grass_tiles = []
            if lane_data["lane_type"] == "grass":
                for _ in range(9):
                    grass_tiles.append(random.choice(self.grass_sprites))

            lane = Lane(lane_data["lane_type"], lane_data["y_pos"], None, grass_tiles)

            for obj_data in lane_data["objects"]:
                obj_type = obj_data["obj_type"]
                goesRight = obj_data["goesRight"]

                if obj_type == "car":
                    sprite = self.car_sprite_right if goesRight else self.car_sprite_left
                elif obj_type == "log":
                    sprite = self.log_sprite
                elif obj_type == "tree":
                    sprite = self.tree_sprite
                elif obj_type == "lilypad":
                    sprite = self.lilypad_sprite

                obj = Object(obj_type, sprite, obj_data["x_pos"], obj_data["y_pos"], obj_data["speed"])
                obj.goesRight = goesRight
                lane.objects.append(obj)

            self.lanes.append(lane)

        self.is_dead = False
        if self.is_paused:
            self.toggle_pause()
        self.game_over_overlay.hide()
        self.game_timer.start(30)
        self.update()
        with open("savegame.json", "w") as f:
            json.dump(save_data, f)
        self.toggle_pause()
        self.log_event("Game saved to savegame.json")

        self.is_dead = False
        if self.is_paused:
            self.toggle_pause()
        self.game_over_overlay.hide()
        self.game_timer.start(30)
        self.update()
        self.log_event("Game loaded from savegame.json")
        return True

    def log_event(self, message):
        print(f"[SCORE: {self.score}] {message}")
    def generate_first_lanes(self):
        for y in [15, 14]:
            grass_tiles = []
            for _ in range(9):
                grass_tiles.append(random.choice(self.grass_sprites))
            self.lanes.append(Lane("grass", y, None, grass_tiles))

        previous_lane_type = "grass"

        for i in range(13, -1, -1):
            lane_types = ["road", "river", "grass"]
            if self.river_block and previous_lane_type == "river":
                lane_types.remove("river")

            lane_type = random.choice(lane_types)
            previous_lane_type = lane_type
            if lane_type == "road":
                lane_direction = random.choice([True, False])
                if lane_direction:
                    current_sprite = self.car_sprite_right
                else:
                    current_sprite = self.car_sprite_left

                lane_objects = []
                for x_start in [1, 5, 9]:
                    if random.random() <= self.spawn_rate:
                        car_speed = random.uniform(0.02, 0.06) + (self.difficulty * 1.8) + random.uniform(0.0, 0.04)
                        obj = Object("car", current_sprite, x_start, i, car_speed)
                        obj.goesRight = lane_direction
                        lane_objects.append(obj)

                if not lane_objects:
                    car_speed = random.uniform(0.02, 0.06) + (self.difficulty * 1.8)
                    obj = Object("car", current_sprite, 5, i, car_speed)
                    obj.goesRight = lane_direction
                    lane_objects.append(obj)

                self.lanes.append(Lane(lane_type, i, lane_objects))
            elif lane_type == "grass":
                grass_tiles = []
                for _ in range(9):
                    grass_tiles.append(random.choice(self.grass_sprites))

                tree_objects = []
                num_trees = random.randint(1, 4)
                tree_x_positions = random.sample(range(9), num_trees)

                for tx in tree_x_positions:
                    tree_objects.append(Object("tree", self.tree_sprite, tx, i, 0))

                self.lanes.append(Lane(lane_type, i, tree_objects, grass_tiles))
            elif lane_type == "river":
                lane_speed = random.uniform(0.02, 0.05)
                lane_direction = random.choice([True, False])

                if random.uniform(0, 1.0) > 0.5:
                    lane_objects = [
                        Object("log", self.log_sprite, 1, i, lane_speed),
                        Object("log", self.log_sprite, 4, i, lane_speed),
                        Object("log", self.log_sprite, 7, i, lane_speed),
                    ]
                else:
                    lane_objects = []
                    num_pads = random.randint(5, 7)
                    pad_positions = random.sample(range(9), num_pads)
                    for px in pad_positions:
                        lane_objects.append(Object("lilypad", self.lilypad_sprite, px, i, 0))

                for obj in lane_objects:
                    obj.goesRight = lane_direction

                self.lanes.append(Lane(lane_type, i, lane_objects))

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
        cell_size = game_width / self.tile_size

        game_rect = QRect(x_offset, y_offset, game_width, game_height)
        painter.setClipRect(game_rect)
        painter.fillRect(game_rect, QColor(40, 40, 40))

        for lane in self.lanes:
            lane_y = y_offset + int(lane.y_pos * cell_size)
            lane_h = int(cell_size) + 1

            if lane.lane_type == "grass":
                for tile_index in range(9):
                    tile_x = x_offset + int(tile_index * cell_size)
                    painter.drawPixmap(tile_x, lane_y, int(cell_size) + 1, lane_h, lane.tiles[tile_index])
            elif lane.lane_type == "road":
                for tile_index in range(9):
                    tile_x = x_offset + int(tile_index * cell_size)
                    painter.drawPixmap(tile_x, lane_y, int(cell_size) + 1, lane_h, self.road_sprite)
            elif lane.lane_type == "river":
                for tile_index in range(9):
                    tile_x = x_offset + int(tile_index * cell_size)
                    painter.drawPixmap(tile_x, lane_y, int(cell_size) + 1, lane_h, self.water_sprite)

            for obj in lane.objects:
                obj_x = x_offset + int(obj.x_pos * cell_size)
                painter.drawPixmap(obj_x, lane_y, int(cell_size) + 1, lane_h, obj.sprite)

                if self.debug_mode:
                    obj_left, obj_right = obj.get_hitbox()
                    hitbox_x = x_offset + int(obj_left * cell_size)
                    hitbox_w = int((obj_right - obj_left) * cell_size)

                    painter.setPen(QColor(255, 0, 0))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(hitbox_x, lane_y, hitbox_w, int(cell_size))

                    painter.setPen(QColor(0, 255, 0))
                    debug_font = QFont("Arial", 8)
                    painter.setFont(debug_font)
                    speed_str = f"{obj.speed:.2f}"
                    painter.drawText(hitbox_x + 2, lane_y + 12, obj.obj_type)
                    painter.drawText(hitbox_x + 2, lane_y + 24, speed_str)

        pixel_x = x_offset + int(self.player_x * cell_size)
        pixel_y = y_offset + int(self.player_y * cell_size)
        painter.drawPixmap(pixel_x, pixel_y, int(cell_size), int(cell_size), self.player_sprite)

        if self.debug_mode:
            player_left = self.player_x + 0.25
            player_right = self.player_x + 0.75
            p_hitbox_x = x_offset + int(player_left * cell_size)
            p_hitbox_w = int((player_right - player_left) * cell_size)

            painter.setPen(QColor(0, 0, 255))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(p_hitbox_x, pixel_y, p_hitbox_w, int(cell_size))

        painter.setClipping(False)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont(self.font().family(), self.font().pointSize()))
        painter.drawText(x_offset + 20, y_offset + 40, f"Score: {self.score}")

        if self.debug_mode:
            painter.drawText(x_offset + 20, y_offset + 70, f"Difficulty: {self.difficulty:.4f}")
            painter.drawText(x_offset + 20, y_offset + 100, f"Spawn Rate: {self.spawn_rate:.2f}")

    def is_tree_at(self, target_x, target_y):
        for lane in self.lanes:
            if lane.y_pos == target_y:
                for obj in lane.objects:
                    if obj.obj_type == "tree" and obj.x_pos == target_x:
                        return True
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.toggle_pause()
            return

        if self.is_paused:
            return

        current_grid_x = round(self.player_x)

        if (event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_W) and not self.is_dead:
            if self.is_tree_at(current_grid_x, self.player_y - 1):
                return

            self.player_x = current_grid_x
            self.absolute_y += 1
            if self.absolute_y > self.score:
                self.score = self.absolute_y
                self.difficulty = self.score * 0.0001
                self.spawn_rate = min(0.5 + self.difficulty * 10, 0.95)
                self.log_event(f"New max score. Difficulty: {self.difficulty:.4f}, Spawn Rate: {self.spawn_rate:.2f}")

            self.log_event(f"Moved UP. Grid Y: {self.player_y - 1}")

            if self.player_y > 8:
                self.player_y -= 1
            else:
                top_lane_type = "grass"
                for lane in self.lanes:
                    if lane.y_pos == 0:
                        top_lane_type = lane.lane_type
                    lane.y_pos += 1

                lane_types = ["road", "river", "grass"]
                if self.river_block and top_lane_type == "river":
                    lane_types.remove("river")

                new_lane_type = random.choice(lane_types)

                if new_lane_type == "road":
                    lane_direction = random.choice([True, False])
                    if lane_direction:
                        current_sprite = self.car_sprite_right
                    else:
                        current_sprite = self.car_sprite_left

                    lane_objects = []
                    for x_start in [1, 5, 9]:
                        if random.random() <= self.spawn_rate:
                            car_speed = random.uniform(0.02, 0.06) + (self.difficulty * 1.8) + random.uniform(0.0, 0.04)
                            obj = Object("car", current_sprite, x_start, 0, car_speed)
                            obj.goesRight = lane_direction
                            lane_objects.append(obj)

                    if not lane_objects:
                        car_speed = random.uniform(0.02, 0.06) + (self.difficulty * 1.8)
                        obj = Object("car", current_sprite, 5, 0, car_speed)
                        obj.goesRight = lane_direction
                        lane_objects.append(obj)

                    self.lanes.append(Lane(new_lane_type, 0, lane_objects))

                elif new_lane_type == "grass":
                    grass_tiles = []
                    for _ in range(9):
                        grass_tiles.append(random.choice(self.grass_sprites))

                    tree_objects = []
                    num_trees = random.randint(1, 4)
                    tree_x_positions = random.sample(range(9), num_trees)

                    for tx in tree_x_positions:
                        tree_objects.append(Object("tree", self.tree_sprite, tx, 0, 0))

                    self.lanes.append(Lane(new_lane_type, 0, tree_objects, grass_tiles))

                elif new_lane_type == "river":
                    lane_speed = random.uniform(0.02, 0.05) + self.difficulty
                    lane_direction = random.choice([True, False])
                    if random.uniform(0, 1.0) > max((0.5 - self.difficulty * 20), 0.1):
                        lane_objects = [
                            Object("log", self.log_sprite, 1, 0, lane_speed),
                            Object("log", self.log_sprite, 4, 0, lane_speed),
                            Object("log", self.log_sprite, 7, 0, lane_speed),
                        ]
                    else:
                        lane_objects = []
                        num_pads = random.randint(5, 7)
                        pad_positions = random.sample(range(9), num_pads)
                        for px in pad_positions:
                            lane_objects.append(Object("lilypad", self.lilypad_sprite, px, 0, 0))

                    for obj in lane_objects:
                        obj.goesRight = lane_direction

                    self.lanes.append(Lane(new_lane_type, 0, lane_objects))
            self.lanes = [lane for lane in self.lanes if lane.y_pos <= 15]

        elif (event.key() == Qt.Key.Key_Down or event.key() == Qt.Key.Key_S) and not self.is_dead:
            if self.is_tree_at(current_grid_x, self.player_y + 1):
                return
            self.player_x = current_grid_x
            self.player_y += 1
            self.absolute_y -= 1
            self.log_event(f"Moved DOWN. Grid Y: {self.player_y}")
        elif (event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_A) and not self.is_dead:
            if self.is_tree_at(current_grid_x - 1, self.player_y):
                return
            self.player_x = current_grid_x - 1
            self.log_event(f"Moved LEFT. Grid X: {self.player_x}")

        elif (event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_D) and not self.is_dead:
            if self.is_tree_at(current_grid_x + 1, self.player_y):
                return
            self.player_x = current_grid_x + 1
            self.log_event(f"Moved RIGHT. Grid X: {self.player_x}")
        elif event.key() == Qt.Key.Key_R:
            self.reset_game()

        self.update()

    def get_lane(self, y):
        for lane in self.lanes:
            if lane.y_pos == y:
                return lane
        return None

    def ai_step(self):
        if not self.ai_mode or self.is_dead or self.is_paused:
            return

        if not hasattr(self, 'stuck_ticks'):
            self.stuck_ticks = 0
        if not hasattr(self, 'last_y'):
            self.last_y = self.player_y
        if not hasattr(self, 'last_x'):
            self.last_x = self.player_x
        if not hasattr(self, 'history_path'):
            self.history_path = []

        if round(self.player_y) == round(self.last_y) and round(self.player_x) == round(self.last_x):
            self.stuck_ticks += 1
        else:
            self.stuck_ticks = 0
            current_pos = (round(self.player_x), self.absolute_y)
            self.history_path.append(current_pos)
            if len(self.history_path) > 15:
                self.history_path.pop(0)

        self.last_y = self.player_y
        self.last_x = self.player_x

        current_x = round(self.player_x)
        current_y = round(self.player_y)
        best_move = None
        max_score = -9999

        moves = [(0, -1), (-1, 0), (1, 0), (0, 0), (0, 1)]

        for dx, dy in moves:
            tx = current_x + dx
            ty = current_y + dy

            if tx < 0 or tx > 8:
                continue
            if self.is_tree_at(tx, ty):
                continue

            lane = self.get_lane(ty)
            if not lane:
                continue

            is_safe = True
            if lane.lane_type == "road":
                for obj in lane.objects:
                    obj_l, obj_r = obj.get_hitbox()
                    margin = obj.speed * 8
                    if obj.goesRight:
                        obj_r += margin
                        obj_l -= 0.1
                    else:
                        obj_l -= margin
                        obj_r += 0.1
                    if tx + 0.2 < obj_r and tx + 0.8 > obj_l:
                        is_safe = False
                        break
            elif lane.lane_type == "river":
                on_platform = False
                for obj in lane.objects:
                    obj_l, obj_r = obj.get_hitbox()
                    if obj.obj_type == "log":
                        if obj.goesRight:
                            obj_l += obj.speed * 8
                            obj_r -= obj.speed * 2
                        else:
                            obj_r -= obj.speed * 8
                            obj_l += obj.speed * 2
                    if tx + 0.4 >= obj_l and tx + 0.6 <= obj_r:
                        on_platform = True
                        break
                if not on_platform:
                    is_safe = False

            if is_safe:
                score = 0
                if dy == -1:
                    score += 100
                elif dy == 1:
                    score -= 50
                elif dx != 0:
                    score -= 10
                elif dx == 0 and dy == 0:
                    score -= 5

                target_world_pos = (tx, self.absolute_y - dy)
                if target_world_pos in self.history_path:
                    visits = self.history_path.count(target_world_pos)
                    score -= 150 * visits

                current_lane = self.get_lane(current_y)
                if current_lane and current_lane.lane_type == "road" and dx == 0 and dy == 0:
                    score -= 30

                front_ty = ty - 1
                lane1 = self.get_lane(front_ty)
                lane2 = self.get_lane(front_ty - 1)

                is_moving_log = False
                if lane and lane.lane_type == "river":
                    for o in lane.objects:
                        if o.speed > 0:
                            is_moving_log = True

                forward_clear = True
                if not is_moving_log:
                    if lane1:
                        if lane1.lane_type == "grass" and self.is_tree_at(tx, front_ty):
                            forward_clear = False
                        elif lane1.lane_type == "river":
                            is_lily = True
                            has_plat = False
                            for o in lane1.objects:
                                if o.speed > 0:
                                    is_lily = False
                                ol, or_ = o.get_hitbox()
                                if tx + 0.5 >= ol and tx + 0.5 <= or_:
                                    has_plat = True
                            if is_lily and not has_plat:
                                forward_clear = False

                    if forward_clear and lane2:
                        if lane2.lane_type == "grass" and self.is_tree_at(tx, front_ty - 1):
                            forward_clear = False
                        elif lane2.lane_type == "river":
                            is_lily = True
                            has_plat = False
                            for o in lane2.objects:
                                if o.speed > 0:
                                    is_lily = False
                                ol, or_ = o.get_hitbox()
                                if tx + 0.5 >= ol and tx + 0.5 <= or_:
                                    has_plat = True
                            if is_lily and not has_plat:
                                forward_clear = False

                if not forward_clear:
                    if dy == -1:
                        score -= 200
                    elif dy == 0 and dx == 0:
                        score -= 50

                best_cx_dist = 999
                for cx in range(9):
                    valid = True
                    if self.is_tree_at(cx, ty):
                        valid = False

                    if valid and lane1:
                        if lane1.lane_type == "grass" and self.is_tree_at(cx, front_ty):
                            valid = False
                        elif lane1.lane_type == "river":
                            is_lily = True
                            has_plat = False
                            for o in lane1.objects:
                                if o.speed > 0:
                                    is_lily = False
                                ol, or_ = o.get_hitbox()
                                if cx + 0.5 >= ol and cx + 0.5 <= or_:
                                    has_plat = True
                            if is_lily and not has_plat:
                                valid = False

                    if valid and lane2:
                        if lane2.lane_type == "grass" and self.is_tree_at(cx, front_ty - 1):
                            valid = False
                        elif lane2.lane_type == "river":
                            is_lily = True
                            has_plat = False
                            for o in lane2.objects:
                                if o.speed > 0:
                                    is_lily = False
                                ol, or_ = o.get_hitbox()
                                if cx + 0.5 >= ol and cx + 0.5 <= or_:
                                    has_plat = True
                            if is_lily and not has_plat:
                                valid = False

                    if valid:
                        dist = abs(tx - cx)
                        if dist < best_cx_dist:
                            best_cx_dist = dist

                if best_cx_dist != 999:
                    score -= best_cx_dist * 20

                if self.stuck_ticks > 20:
                    if dx == 0 and dy == 0:
                        score -= 500
                    if dy == 1:
                        score += 250

                if score > max_score:
                    max_score = score
                    best_move = (dx, dy)

        if best_move:
            dx, dy = best_move
            key = None
            if dx == 0 and dy == -1:
                key = Qt.Key.Key_Up
            elif dx == -1 and dy == 0:
                key = Qt.Key.Key_Left
            elif dx == 1 and dy == 0:
                key = Qt.Key.Key_Right
            elif dx == 0 and dy == 1:
                key = Qt.Key.Key_Down

            if key:
                event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
                QApplication.postEvent(self, event)
    def update_game_state(self):
        player_on_log = False
        current_lane_type = "grass"

        for lane in self.lanes:
            if lane.y_pos == self.player_y:
                current_lane_type = lane.lane_type

            if lane.lane_type == "road" and len(lane.objects) > 1:
                lane.objects.sort(key=lambda c: c.x_pos)
                direction_right = lane.objects[0].goesRight
                num_cars = len(lane.objects)
                for j in range(num_cars):
                    if direction_right:
                        front_car = lane.objects[(j + 1) % num_cars]
                        dist = front_car.x_pos - lane.objects[j].x_pos
                        if dist < 0:
                            dist += 16
                        if dist < 2.5 and lane.objects[j].speed > front_car.speed:
                            self.log_event(
                                f"Car braking: {lane.objects[j].speed:.3f} -> {front_car.speed:.3f} to avoid crash.")
                            lane.objects[j].speed = front_car.speed
                    else:
                        front_car = lane.objects[(j - 1) % num_cars]
                        dist = lane.objects[j].x_pos - front_car.x_pos
                        if dist < 0:
                            dist += 16
                        if dist < 2.5 and lane.objects[j].speed > front_car.speed:
                            self.log_event(
                                f"Car braking: {lane.objects[j].speed:.3f} -> {front_car.speed:.3f} to avoid crash.")
                            lane.objects[j].speed = front_car.speed

            for obj in lane.objects:
                if obj.goesRight:
                    obj.x_pos += obj.speed
                else:
                    obj.x_pos -= obj.speed

                if lane.y_pos == self.player_y:
                    obj_left, obj_right = obj.get_hitbox()
                    player_left = self.player_x + 0.25
                    player_right = self.player_x + 0.75

                    if player_left < obj_right and player_right > obj_left:
                        if obj.obj_type == "car":
                            if not self.god_mode:
                                self.game_over()
                        elif obj.obj_type == "log":
                            player_on_log = True
                            if obj.goesRight:
                                self.player_x += obj.speed
                            else:
                                self.player_x -= obj.speed
                        elif obj.obj_type == "lilypad":
                            player_on_log = True

                if obj.x_pos > 12:
                    obj.x_pos = -4
                elif obj.x_pos < -4:
                    obj.x_pos = 12

        if current_lane_type == "river" and not player_on_log:
            if not self.god_mode:
                self.game_over()

        if self.player_x < -1 or self.player_x > 9:
            if not self.god_mode:
                self.game_over()

        self.update()

class Options(QWidget):
    back_to_menu = pyqtSignal()
    change_resolution = pyqtSignal(str)
    god_mode_changed = pyqtSignal(bool)
    debug_mode_changed = pyqtSignal(bool)
    river_block_changed = pyqtSignal(bool)
    ai_mode_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("options_screen")

        self.setStyleSheet("""
            QWidget#options_screen {
                background-color: #2b2b2b; 
            }
            QPushButton {
                background-color: #e74c3c; 
                color: white;  
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
                min-width: 250px;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton#toggle_btn {
                background-color: transparent;
                border: none;
            }
            QPushButton#toggle_btn:hover {
                background-color: transparent;
                color: #bdc3c7;
            }
            QComboBox {
                background-color: white;
                color: black;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                min-width: 230px;
                min-height: 55px;
                padding-left: 15px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #bdc3c7;
                color: black;
                border-radius: 5px;
            }
            QLabel {
                color: white;
                font-size: 40px;
                font-weight: bold;
                margin-bottom: 20px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(25)

        title = QLabel("Options", self)

        self.res_options = QComboBox(self)
        self.res_options.addItems(["360x640", "480x852", "720x1280", "1080x1920", "Fullscreen"])

        pixmap_unchecked = QPixmap("sprites/gui/not_checked.png").scaled(
            32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )
        pixmap_checked = QPixmap("sprites/gui/checked.png").scaled(
            32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )

        toggle_icon = QIcon()
        toggle_icon.addPixmap(pixmap_unchecked, QIcon.Mode.Normal, QIcon.State.Off)
        toggle_icon.addPixmap(pixmap_checked, QIcon.Mode.Normal, QIcon.State.On)

        self.god_mode_btn = QPushButton(" God Mode", self)
        self.god_mode_btn.setObjectName("toggle_btn")
        self.god_mode_btn.setCheckable(True)
        self.god_mode_btn.setIcon(toggle_icon)
        self.god_mode_btn.setIconSize(QSize(32, 32))
        self.god_mode_btn.toggled.connect(self.emit_god_mode)

        self.debug_mode_btn = QPushButton(" Debug Mode", self)
        self.debug_mode_btn.setObjectName("toggle_btn")
        self.debug_mode_btn.setCheckable(True)
        self.debug_mode_btn.setIcon(toggle_icon)
        self.debug_mode_btn.setIconSize(QSize(32, 32))
        self.debug_mode_btn.toggled.connect(self.emit_debug_mode)

        self.ai_mode_btn = QPushButton(" AI Bot", self)
        self.ai_mode_btn.setObjectName("toggle_btn")
        self.ai_mode_btn.setCheckable(True)
        self.ai_mode_btn.setIcon(toggle_icon)
        self.ai_mode_btn.setIconSize(QSize(32, 32))
        self.ai_mode_btn.toggled.connect(self.emit_ai_mode)

        self.river_block_btn = QPushButton(" 2 River block", self)
        self.river_block_btn.setObjectName("toggle_btn")
        self.river_block_btn.setCheckable(True)
        self.river_block_btn.setChecked(True)
        self.river_block_btn.setIcon(toggle_icon)
        self.river_block_btn.setIconSize(QSize(32, 32))
        self.river_block_btn.toggled.connect(self.emit_river_block)

        self.apply_btn = QPushButton("Confirm settings", self)
        self.apply_btn.clicked.connect(self.apply_settings)

        self.back_btn = QPushButton("Back", self)
        self.back_btn.clicked.connect(lambda: self.back_to_menu.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.res_options, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.god_mode_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.debug_mode_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.river_block_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ai_mode_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.apply_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        self.setLayout(layout)

    def apply_settings(self):
        selected_resolution = self.res_options.currentText()
        self.change_resolution.emit(selected_resolution)

    def emit_god_mode(self, state):
        self.god_mode_changed.emit(state)

    def emit_debug_mode(self, state):
        self.debug_mode_changed.emit(state)

    def emit_river_block(self, state):
        self.river_block_changed.emit(state)
    def emit_ai_mode(self, state):
        self.ai_mode_changed.emit(state)

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
                        font-size: 16px;
                        font-weight: bold;
                        font-family: Press Start 2P;
                        min-width: 250px;
                        min-height: 55px;
                    }
                    QPushButton:hover{
                        background-color: #c0392b;
                    }
                    QLabel{
                        color: rgb(255, 255, 255);
                        font-family: Press Start 2P;
                        font-size: 24px;
                        font-weight: bold;
                    }
                    QLabel#author{
                        font-size: 12px;
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
        self.option_btn = QPushButton("Options", self)
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

    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "sprites", "PressStart2P.ttf")

    font_id = QFontDatabase.addApplicationFont(font_path)

    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        global_font = QFont(font_family)
        app.setFont(global_font)

    app.setWindowIcon(QIcon(os.path.join(base_dir, 'sprites', 'amogus.png')))
    ex = MainApp()
    ex.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()