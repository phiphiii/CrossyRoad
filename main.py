import sys
import random
import os
import json

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize, QRect, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QComboBox, QLineEdit, QGraphicsBlurEffect
from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap, QTransform, QFontDatabase, QFont, QKeyEvent
from PyQt6.QtNetwork import QTcpSocket


class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("phiphi's Crossy Road")
        self.setFixedSize(360, 640)

        self.bg_label = QLabel(self)
        self.bg_pixmap = QPixmap("sprites/gui/background.png")
        self.bg_label.setPixmap(self.bg_pixmap)
        self.bg_label.setScaledContents(True)

        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(5)
        self.bg_label.setGraphicsEffect(blur_effect)

        main_layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")

        self.menu = Menu()
        self.singleplayer_menu = SingleplayerMenu()
        self.multiplayer_menu = MultiplayerMenu()
        self.game = Game()
        self.options_screen = Options()
        self.lobby_menu = LobbyMenu()

        self.stacked_widget.addWidget(self.menu)
        self.stacked_widget.addWidget(self.singleplayer_menu)
        self.stacked_widget.addWidget(self.multiplayer_menu)
        self.stacked_widget.addWidget(self.game)
        self.stacked_widget.addWidget(self.options_screen)
        self.stacked_widget.addWidget(self.lobby_menu)

        self.setLayout(main_layout)
        main_layout.addWidget(self.stacked_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.previous_index = 0

        self.menu.singleplayer.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.menu.multiplayer.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.menu.options.connect(self.open_options)

        self.singleplayer_menu.back.connect(self.back_to_main)
        self.singleplayer_menu.new_game.connect(self.start_new_game)
        self.singleplayer_menu.load_game.connect(self.load_saved_game)

        self.multiplayer_menu.back.connect(self.back_to_main)
        self.multiplayer_menu.join_game.connect(self.start_multiplayer_game)

        self.lobby_menu.back.connect(self.back_to_main)
        self.lobby_menu.ready.connect(self.game.send_ready)
        self.lobby_menu.unready.connect(self.game.send_unready)

        self.options_screen.back_to_menu.connect(self.back_from_options)
        self.options_screen.change_resolution.connect(self.change_res)
        self.options_screen.god_mode_changed.connect(self.update_god_mode)
        self.options_screen.debug_mode_changed.connect(self.update_debug_mode)
        self.options_screen.ai_mode_changed.connect(self.update_ai_mode)

        self.game.open_options.connect(self.open_options)
        self.game.back_to_main.connect(self.back_to_main)
        self.game.lobby_updated.connect(self.lobby_menu.update_lobby)
        self.game.game_started.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.game.countdown_started.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.game.countdown_started.connect(self.lobby_menu.lock_buttons)
        self.game.rematch_requested.connect(self.handle_rematch)

    def load_saved_game(self):
        if self.game.load_game():
            self.stacked_widget.setCurrentIndex(3)
            self.game.setFocus()

    def start_new_game(self):
        self.game.is_multiplayer = False
        self.game.reset_game()
        self.stacked_widget.setCurrentIndex(3)
        self.game.setFocus()

    def start_multiplayer_game(self, nickname):
        self.game.is_multiplayer = True
        self.game.connect_to_server(nickname)
        self.game.reset_game()
        self.stacked_widget.setCurrentIndex(5)
        self.lobby_menu.is_ready = False
        self.lobby_menu.unlock_buttons()
        self.lobby_menu.ready_btn.setText("Ready (0/0)")

    def handle_rematch(self):
        self.game.is_waiting_for_players = True
        self.lobby_menu.is_ready = False
        self.lobby_menu.unlock_buttons()
        self.stacked_widget.setCurrentIndex(5)

    def open_options(self):
        self.previous_index = self.stacked_widget.currentIndex()
        self.stacked_widget.setCurrentIndex(4)

    def back_from_options(self):
        self.stacked_widget.setCurrentIndex(self.previous_index)
        if self.previous_index == 3:
            self.game.setFocus()

    def back_to_main(self):
        if self.game.tcp_client.state() == QTcpSocket.SocketState.ConnectedState:
            self.game.tcp_client.abort()
        self.lobby_menu.unlock_buttons()
        self.lobby_menu.is_ready = False
        self.lobby_menu.ready_btn.setText("Ready (0/0)")
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

    def resizeEvent(self, event):
        self.bg_label.resize(self.width(), self.height())
        super().resizeEvent(event)

    def update_god_mode(self, state):
        self.game.god_mode = state

    def update_debug_mode(self, state):
        self.game.debug_mode = state

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

class ObjectFactory:
    def __init__(self, game):
        self.game = game

    def create(self, obj_type, x, y, speed=0.0, goes_right=None):
        sprite = None
        if obj_type == "car":
            sprite = self.game.car_sprite_right if goes_right else self.game.car_sprite_left
        elif obj_type == "log":
            sprite = self.game.log_sprite
        elif obj_type == "tree":
            sprite = self.game.tree_sprite
        elif obj_type == "lilypad":
            sprite = self.game.lilypad_sprite

        obj = Object(obj_type, sprite, x, y, speed)
        if goes_right is not None:
            obj.goesRight = goes_right
        return obj

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
    lobby_updated = pyqtSignal(str, str)
    game_started = pyqtSignal()
    countdown_started = pyqtSignal()
    rematch_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tile_size = 9
        self.player_x = 4
        self.player_y = 14

        self.last_sent_x = None
        self.last_sent_y = None
        self.last_sent_score = None
        self.multiplayer_scores = {}
        self.is_waiting_for_players = False

        self.load_config()

        self.absolute_y = 0
        self.score = 0
        self.difficulty = self.config["base_difficulty"]
        self.spawn_rate = self.config["base_spawn_rate"]
        self.camera_scroll = 0.0

        self.current_seed = random.randint(0, 999999999)
        random.seed(self.current_seed)

        self.current_tick = 0
        self.recorded_inputs = []
        self.is_replay_mode = False
        self.replay_index = 0

        self.god_mode = False
        self.debug_mode = False
        self.ai_mode = False
        self.is_paused = False
        self.is_dead = False
        self.is_multiplayer = False

        self.tcp_client = QTcpSocket(self)
        self.tcp_client.connected.connect(self.on_connected)
        self.tcp_client.readyRead.connect(self.read_network_data)
        self.player_nickname = ""

        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self.send_player_state)
        self.network_timer.start(100)

        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self.ai_step)
        self.ai_timer.start(self.config["ai_tickrate"])

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

        self.factory = ObjectFactory(self)
        self.generate_first_lanes()

        self.pause_overlay = QWidget(self)
        self.pause_overlay.setStyleSheet("""
            QWidget { background-color: rgba(0, 0, 0, 180); }
            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                border-radius: 12px;
                font-size: 20px;
                font-family: "Press Start 2P";
                min-width: 250px;
                min-height: 55px;
            }
            QPushButton:hover { background-color: #c0392b; }
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
        self.restart_btn.clicked.connect(lambda checked: self.reset_game(False))
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

        self.game_over_overlay = QWidget(self)
        self.game_over_overlay.setStyleSheet("""
            QWidget { background-color: rgba(0, 0, 0, 200); }
            QLabel#title { color: red; font-size: 32px; font-weight: bold; background: transparent; }
            QLabel#score { color: white; font-size: 24px; background: transparent; }
            QPushButton { background-color: #e74c3c; color: white; border-radius: 12px; font-size: 16px; min-width: 250px; min-height: 55px; margin-top: 10px; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        game_over_layout = QVBoxLayout(self.game_over_overlay)

        self.go_label = QLabel("GAME OVER", self.game_over_overlay)
        self.go_label.setObjectName("title")
        self.go_score_label = QLabel("Score: 0", self.game_over_overlay)
        self.go_score_label.setObjectName("score")

        self.go_load_btn = QPushButton("Load Save", self.game_over_overlay)
        self.go_replay_btn = QPushButton("Replay Mode", self.game_over_overlay)
        self.go_restart_btn = QPushButton("Restart", self.game_over_overlay)
        self.go_menu_btn = QPushButton("Main Menu", self.game_over_overlay)

        self.go_load_btn.clicked.connect(self.load_game)
        self.go_replay_btn.clicked.connect(lambda checked: self.reset_game(True))
        self.go_restart_btn.clicked.connect(self.handle_restart_clicked)
        self.go_menu_btn.clicked.connect(lambda: self.back_to_main.emit())

        game_over_layout.addStretch()
        game_over_layout.addWidget(self.go_label, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addWidget(self.go_score_label, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addSpacing(30)
        game_over_layout.addWidget(self.go_load_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addWidget(self.go_replay_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addWidget(self.go_restart_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addWidget(self.go_menu_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        game_over_layout.addStretch()
        self.game_over_overlay.hide()

        self.countdown_overlay = QWidget(self)
        self.countdown_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        cd_layout = QVBoxLayout(self.countdown_overlay)
        self.countdown_label = QLabel("", self.countdown_overlay)
        self.countdown_label.setStyleSheet("color: white; font-size: 80px; font-weight: bold; background: transparent;")
        cd_layout.addWidget(self.countdown_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.countdown_overlay.hide()

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.update_game_state)
        self.game_timer.start(self.config["game_timer_ms"])

    def handle_restart_clicked(self):
        if getattr(self, 'is_multiplayer', False):
            if self.tcp_client.state() == QTcpSocket.SocketState.ConnectedState:
                self.tcp_client.write("REMATCH\n".encode('utf-8'))
                self.go_restart_btn.setText("Waiting for others...")
                self.go_restart_btn.setEnabled(False)
        else:
            self.reset_game(False)

    def send_player_state(self):
        if self.tcp_client.state() == QTcpSocket.SocketState.ConnectedState and not getattr(self, 'is_waiting_for_players', False):
            current_x = round(self.player_x, 1)
            current_y = round(self.player_y, 1)
            current_abs_y = self.absolute_y

            if not hasattr(self, 'last_sent_abs_y'):
                self.last_sent_abs_y = None

            if current_x != self.last_sent_x or current_y != self.last_sent_y or current_abs_y != self.last_sent_abs_y or self.score != self.last_sent_score:
                state_payload = f"STATE_X:{current_x}|STATE_Y:{current_y}|ABS_Y:{current_abs_y}|SCORE:{self.score}\n"
                self.tcp_client.write(state_payload.encode('utf-8'))
                self.last_sent_x = current_x
                self.last_sent_y = current_y
                self.last_sent_abs_y = current_abs_y
                self.last_sent_score = self.score

    def log_event(self, message):
        print(f"[SCORE: {self.score}] {message}")

    def read_network_data(self):
        if not hasattr(self, 'multiplayer_positions'):
            self.multiplayer_positions = {}

        while self.tcp_client.canReadLine():
            line = self.tcp_client.readLine().data().decode('utf-8').strip()
            if not line:
                continue

            if line.startswith("LOBBY:"):
                parts = line[6:].split('|')
                if len(parts) == 2:
                    for p in parts[0].split(','):
                        if p and p != self.player_nickname:
                            if p not in self.multiplayer_scores:
                                self.multiplayer_scores[p] = 0
                            if p not in self.multiplayer_positions:
                                self.multiplayer_positions[p] = {'x': 4, 'abs_y': 0}
                    self.lobby_updated.emit(parts[0], parts[1].split(':')[1])

                    if not self.is_waiting_for_players and getattr(self, 'is_multiplayer', False):
                        self.is_waiting_for_players = True
                        self.is_counting_down = False
                        self.game_over_overlay.hide()
                        self.countdown_overlay.hide()
                        self.reset_game(False)
                        self.rematch_requested.emit()

            elif line.startswith("NAME_ACCEPTED:"):
                self.player_nickname = line.split(':', 1)[1]

            elif line.startswith("REMATCH_UPDATE:"):
                status = line.split(':')[1]
                self.go_restart_btn.setText(f"Waiting ({status})")

            elif line.startswith("COUNTDOWN:"):
                self.countdown_started.emit()
                if getattr(self, 'is_dead', False) or self.game_over_overlay.isVisible():
                    self.game_over_overlay.hide()
                    self.reset_game(False)
                self.is_counting_down = True
                num = line.split(':')[1]
                self.countdown_overlay.raise_()
                self.show_countdown(num)

            elif line == "START":
                self.is_counting_down = False
                self.is_waiting_for_players = False
                self.show_countdown("START!")
                self.game_started.emit()
                QTimer.singleShot(1000, self.countdown_overlay.hide)

            elif line.startswith("["):
                try:
                    name_part, data_part = line.split(']: ', 1)
                    name = name_part[1:]
                    if name == self.player_nickname:
                        continue

                    if name not in self.multiplayer_positions:
                        self.multiplayer_positions[name] = {'x': 4, 'abs_y': 0}

                    for item in data_part.split('|'):
                        if item.startswith("SCORE:"):
                            self.multiplayer_scores[name] = int(item.split(':')[1])
                        elif item.startswith("STATE_X:"):
                            self.multiplayer_positions[name]['x'] = float(item.split(':')[1])
                        elif item.startswith("ABS_Y:"):
                            self.multiplayer_positions[name]['abs_y'] = int(item.split(':')[1])
                except:
                    pass

    def send_ready(self):
        if self.tcp_client.state() == QTcpSocket.SocketState.ConnectedState:
            self.tcp_client.write("READY\n".encode('utf-8'))

    def send_unready(self):
        if self.tcp_client.state() == QTcpSocket.SocketState.ConnectedState:
            self.tcp_client.write("UNREADY\n".encode('utf-8'))

    def show_countdown(self, text):
        self.countdown_label.setText(text)
        self.countdown_overlay.show()

    def start_multiplayer_match(self):
        self.countdown_overlay.hide()
        self.is_waiting_for_players = False
        self.game_started.emit()

    def connect_to_server(self, nickname):
        self.player_nickname = nickname
        self.is_waiting_for_players = True
        self.multiplayer_scores = {}
        if self.tcp_client.state() != QTcpSocket.SocketState.ConnectedState:
            self.tcp_client.connectToHost('127.0.0.1', 5555)

    def on_connected(self):
        if self.player_nickname:
            self.tcp_client.write((self.player_nickname + '\n').encode('utf-8'))

    def resizeEvent(self, event):
        self.pause_overlay.resize(self.width(), self.height())
        self.game_over_overlay.resize(self.width(), self.height())
        self.countdown_overlay.resize(self.width(), self.height())
        super().resizeEvent(event)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.game_timer.stop()
            if getattr(self, 'is_multiplayer', False):
                self.save_btn.hide()
                self.restart_btn.hide()
            else:
                self.save_btn.show()
                self.restart_btn.show()
            self.pause_overlay.show()
        else:
            self.game_timer.start(30)
            self.pause_overlay.hide()
            self.setFocus()

    def game_over(self):
        self.is_dead = True
        self.game_timer.stop()
        self.go_score_label.setText(f"Score: {self.score}")

        if getattr(self, 'is_multiplayer', False):
            self.go_load_btn.hide()
            self.go_replay_btn.hide()
            self.go_restart_btn.setText("Rematch")
            self.go_restart_btn.setEnabled(True)
        else:
            self.go_load_btn.show()
            self.go_replay_btn.show()
            self.go_restart_btn.setText("Restart")
            self.go_restart_btn.setEnabled(True)

        self.game_over_overlay.show()
        self.log_event("Player died. Game Over.")

    def reset_game(self, replay=False):
        self.load_config()
        self.player_x = 4
        self.player_y = 14
        self.absolute_y = 0
        self.score = 0
        self.difficulty = self.config["base_difficulty"]
        self.spawn_rate = self.config["base_spawn_rate"]
        self.camera_scroll = 0.0
        self.is_dead = False
        self.lanes = []

        self.last_sent_x = None
        self.last_sent_y = None
        self.last_sent_abs_y = None
        self.last_sent_score = None

        if hasattr(self, 'multiplayer_scores'):
            for k in self.multiplayer_scores:
                self.multiplayer_scores[k] = 0

        if hasattr(self, 'multiplayer_positions'):
            self.multiplayer_positions.clear()

        self.current_tick = 0
        self.is_replay_mode = replay
        self.replay_index = 0

        if not replay:
            self.current_seed = random.randint(0, 999999999)
            self.recorded_inputs = []

        random.seed(self.current_seed)
        self.generate_first_lanes()
        if self.is_paused:
            self.toggle_pause()
        self.game_over_overlay.hide()
        self.game_timer.start(self.config["game_timer_ms"])
        self.update()
        self.log_event("Game started / reset.")

    def save_game(self):
        save_data = {
            "score": self.score,
            "absolute_y": self.absolute_y,
            "player_x": self.player_x,
            "player_y": self.player_y,
            "seed": self.current_seed,
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
        self.game_over_overlay.hide()
        self.game_timer.start(30)
        self.update()
        return True

    def load_game(self):
        if not os.path.exists("savegame.json"):
            return False

        with open("savegame.json", "r") as f:
            save_data = json.load(f)

        self.score = save_data["score"]
        self.difficulty = self.config["base_difficulty"] + (self.score * 0.0001)
        self.spawn_rate = min(self.config["base_spawn_rate"] + self.difficulty * 10, 0.95)
        self.absolute_y = save_data["absolute_y"]
        self.player_x = save_data["player_x"]
        self.player_y = save_data["player_y"]
        self.camera_scroll = 0.0

        self.last_sent_x = None
        self.last_sent_y = None
        self.last_sent_score = None

        self.current_seed = save_data.get("seed", random.randint(0, 999999999))
        random.seed(self.current_seed)

        self.current_tick = 0
        self.recorded_inputs = []
        self.is_replay_mode = False
        self.replay_index = 0

        self.lanes = []
        for lane_data in save_data["lanes"]:
            grass_tiles = []
            if lane_data["lane_type"] == "grass":
                for grass_sprite in range(9):
                    grass_tiles.append(random.choice(self.grass_sprites))

            lane = Lane(lane_data["lane_type"], lane_data["y_pos"], None, grass_tiles)

            for obj_data in lane_data["objects"]:
                obj = self.factory.create(
                    obj_data["obj_type"],
                    obj_data["x_pos"],
                    obj_data["y_pos"],
                    obj_data["speed"],
                    obj_data["goesRight"]
                )
                lane.objects.append(obj)

            self.lanes.append(lane)

        self.is_dead = False
        if self.is_paused:
            self.toggle_pause()
        self.game_over_overlay.hide()
        self.game_timer.start(self.config["game_timer_ms"])
        self.update()
        self.log_event("Game loaded from savegame.json")
        return True

    def generate_first_lanes(self):
        for y in [15, 14]:
            grass_tiles = []
            for _ in range(9):
                grass_tiles.append(random.choice(self.grass_sprites))
            self.lanes.append(Lane("grass", y, None, grass_tiles))

        previous_lane_type = "grass"

        for i in range(13, -2, -1):
            lane_types = list(self.config["lane_weights"])
            if self.river_block and previous_lane_type == "river" and "river" in lane_types:
                lane_types.remove("river")

            lane_type = random.choice(lane_types)
            previous_lane_type = lane_type

            if lane_type == "road":
                lane_direction = random.choice([True, False])
                spawn_positions = []
                check_x = 0
                while check_x < 9:
                    if random.random() <= (self.spawn_rate * 0.8):
                        spawn_positions.append(check_x)
                        check_x += random.randint(2, 3)
                    else:
                        check_x += 1

                if not spawn_positions:
                    spawn_positions.append(random.randint(0, 8))

                lane_objects = []
                for x_pos in spawn_positions:
                    car_speed = random.uniform(self.config["min_car_speed"], self.config["max_car_speed"]) + (
                                self.difficulty * 1.8)
                    obj = self.factory.create("car", x_pos, i, car_speed, lane_direction)
                    lane_objects.append(obj)

                self.lanes.append(Lane(lane_type, i, lane_objects))

            elif lane_type == "grass":
                grass_tiles = []
                for _ in range(9):
                    grass_tiles.append(random.choice(self.grass_sprites))

                tree_objects = []
                num_trees = random.randint(1, self.config["max_trees"])
                tree_x_positions = random.sample(range(9), num_trees)

                for tx in tree_x_positions:
                    tree_objects.append(self.factory.create("tree", tx, i))

                self.lanes.append(Lane(lane_type, i, tree_objects, grass_tiles))

            elif lane_type == "river":
                lane_speed = random.uniform(0.02, 0.05) + self.difficulty
                lane_direction = random.choice([True, False])

                if random.uniform(0, 1.0) > 0.5:
                    lane_objects = []
                    spawn_positions = []
                    check_x = 0
                    log_chance = max(0.4, 0.8 - (self.difficulty * 2.0))

                    while check_x < 9:
                        if random.random() <= log_chance:
                            spawn_positions.append(check_x)
                            check_x += random.randint(3, 4)
                        else:
                            check_x += 1

                    if len(spawn_positions) < 2:
                        spawn_positions = [random.randint(0, 2), random.randint(5, 7)]

                    for x_pos in spawn_positions:
                        obj = self.factory.create("log", x_pos, i, lane_speed, lane_direction)
                        lane_objects.append(obj)
                else:
                    lane_objects = []
                    num_pads = random.randint(5, 7)
                    pad_positions = random.sample(range(9), num_pads)
                    for px in pad_positions:
                        lane_objects.append(self.factory.create("lilypad", px, i))

                for obj in lane_objects:
                    obj.goesRight = lane_direction

                self.lanes.append(Lane(lane_type, i, lane_objects))

            self.lanes = [lane for lane in self.lanes if lane.y_pos <= 15]

    def shift_lanes_down(self):
        top_lane_type = "grass"
        for lane in self.lanes:
            if lane.y_pos == -1:
                top_lane_type = lane.lane_type
            lane.y_pos += 1

        lane_types = list(self.config["lane_weights"])
        if self.river_block and top_lane_type == "river" and "river" in lane_types:
            lane_types.remove("river")

        new_lane_type = random.choice(lane_types)

        lane_objects = []
        grass_tiles = []

        if new_lane_type == "road":
            lane_direction = random.choice([True, False])
            spawn_positions = []
            check_x = 0
            while check_x < 9:
                if random.random() <= (self.spawn_rate * 0.8):
                    spawn_positions.append(check_x)
                    check_x += random.randint(2, 3)
                else:
                    check_x += 1

            if not spawn_positions:
                spawn_positions.append(random.randint(0, 8))

            for x_pos in spawn_positions:
                car_speed = random.uniform(self.config["min_car_speed"], self.config["max_car_speed"]) + (
                            self.difficulty * 1.8)
                obj = self.factory.create("car", x_pos, -1, car_speed, lane_direction)
                lane_objects.append(obj)

            self.lanes.append(Lane(new_lane_type, -1, lane_objects))

        elif new_lane_type == "grass":
            for _ in range(9):
                grass_tiles.append(random.choice(self.grass_sprites))

            num_trees = random.randint(1, self.config["max_trees"])
            tree_x_positions = random.sample(range(9), num_trees)

            for tx in tree_x_positions:
                lane_objects.append(self.factory.create("tree", tx, -1))

            self.lanes.append(Lane(new_lane_type, -1, lane_objects, grass_tiles))

        elif new_lane_type == "river":
            lane_speed = random.uniform(0.02, 0.05) + self.difficulty
            lane_direction = random.choice([True, False])

            if random.uniform(0, 1.0) > max((0.5 - self.difficulty * 20), 0.1):
                lane_objects = []
                spawn_positions = []
                check_x = 0
                log_chance = max(0.4, 0.8 - (self.difficulty * 2.0))

                while check_x < 9:
                    if random.random() <= log_chance:
                        spawn_positions.append(check_x)
                        check_x += random.randint(3, 4)
                    else:
                        check_x += 1

                if len(spawn_positions) < 2:
                    spawn_positions = [random.randint(0, 2), random.randint(5, 7)]

                for x_pos in spawn_positions:
                    obj = self.factory.create("log", x_pos, -1, lane_speed, lane_direction)
                    lane_objects.append(obj)
            else:
                lane_objects = []
                num_pads = random.randint(5, 7)
                pad_positions = random.sample(range(9), num_pads)
                for px in pad_positions:
                    lane_objects.append(self.factory.create("lilypad", px, -1))

            for obj in lane_objects:
                obj.goesRight = lane_direction

            self.lanes.append(Lane(new_lane_type, -1, lane_objects))

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
            lane_y = y_offset + int((lane.y_pos + self.camera_scroll) * cell_size)
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

        if getattr(self, 'is_multiplayer', False):
            if not hasattr(self, 'multiplayer_positions'):
                self.multiplayer_positions = {}
            for name, pos in self.multiplayer_positions.items():
                if name == self.player_nickname: continue
                if 'x' in pos and 'abs_y' in pos:
                    other_x = pos['x']
                    other_abs_y = pos['abs_y']

                    diff_y = other_abs_y - self.absolute_y
                    screen_y = self.player_y - diff_y

                    if -2 <= screen_y <= 16:
                        pixel_x = x_offset + int(other_x * cell_size)
                        pixel_y = y_offset + int((screen_y + self.camera_scroll) * cell_size)

                        painter.setOpacity(0.3)
                        painter.drawPixmap(pixel_x, pixel_y, int(cell_size), int(cell_size), self.player_sprite)
                        painter.setOpacity(1.0)

                        painter.setPen(QColor(255, 255, 255))
                        name_font = QFont(self.font().family(), max(6, int(cell_size / 8)))
                        painter.setFont(name_font)
                        fm = painter.fontMetrics()
                        text_width = fm.horizontalAdvance(name)
                        text_x = pixel_x + int(cell_size / 2) - int(text_width / 2)
                        text_y = pixel_y - 5
                        painter.drawText(text_x, text_y, name)

        pixel_x = x_offset + int(self.player_x * cell_size)
        pixel_y = y_offset + int((self.player_y + self.camera_scroll) * cell_size)
        painter.drawPixmap(pixel_x, pixel_y, int(cell_size), int(cell_size), self.player_sprite)

        painter.setClipping(False)
        painter.setFont(QFont(self.font().family(), self.font().pointSize()))
        y_text_pos = y_offset + 40

        if getattr(self, 'is_multiplayer', False):
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(x_offset + 20, y_text_pos, f"{self.player_nickname}: {self.score}")

            painter.setPen(QColor(255, 255, 255))
            if self.tcp_client.state() == QTcpSocket.SocketState.ConnectedState:
                for name, score in self.multiplayer_scores.items():
                    if name == self.player_nickname:
                        continue
                    y_text_pos += 30
                    painter.drawText(x_offset + 20, y_text_pos, f"{name}: {score}")
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(x_offset + 20, y_text_pos, f"Score: {self.score}")

    def is_tree_at(self, target_x, target_y):
        for lane in self.lanes:
            if lane.y_pos == target_y:
                for obj in lane.objects:
                    if obj.obj_type == "tree" and obj.x_pos == target_x:
                        return True
        return False

    def keyPressEvent(self, event, simulated=False):
        if getattr(self, 'is_waiting_for_players', False) or getattr(self, 'is_counting_down', False):
            return

        if event.key() == Qt.Key.Key_Escape:
            if getattr(self, 'is_dead', False):
                return
            self.toggle_pause()
            return

        if self.is_paused: return

        if event.key() == Qt.Key.Key_R:
            if not getattr(self, 'is_multiplayer', False):
                self.reset_game(False)
            return

        if event.key() == Qt.Key.Key_Q:
            self.load_config()
            return

        if self.is_replay_mode and not simulated: return

        valid_keys = [Qt.Key.Key_Up, Qt.Key.Key_W, Qt.Key.Key_Down, Qt.Key.Key_S, Qt.Key.Key_Left, Qt.Key.Key_A,
                      Qt.Key.Key_Right, Qt.Key.Key_D]
        if not self.is_replay_mode and not self.is_dead and event.key() in valid_keys:
            self.recorded_inputs.append((self.current_tick, event.key()))

        current_grid_x = round(self.player_x)

        if (event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_W) and not self.is_dead:
            if self.is_tree_at(current_grid_x, self.player_y - 1): return
            self.player_x = current_grid_x
            self.absolute_y += 1
            if self.absolute_y > self.score:
                self.score = self.absolute_y
                self.difficulty = self.score * 0.0001
                self.spawn_rate = min(0.3 + self.difficulty * 10, 0.95)
                self.log_event(f"New max score. Difficulty: {self.difficulty:.4f}, Spawn Rate: {self.spawn_rate:.2f}")

            self.log_event(f"Moved UP. Grid Y: {self.player_y - 1}")

            if self.player_y > 8:
                self.player_y -= 1
            else:
                self.shift_lanes_down()

        elif (event.key() == Qt.Key.Key_Down or event.key() == Qt.Key.Key_S) and not self.is_dead:
            if self.is_tree_at(current_grid_x, self.player_y + 1): return
            self.player_x = current_grid_x
            self.player_y += 1
            self.absolute_y -= 1
            self.log_event(f"Moved DOWN. Grid Y: {self.player_y}")

        elif (event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_A) and not self.is_dead:
            if self.is_tree_at(current_grid_x - 1, self.player_y): return
            self.player_x = current_grid_x - 1
            self.log_event(f"Moved LEFT. Grid X: {self.player_x}")

        elif (event.key() == Qt.Key.Key_Right or event.key() == Qt.Key.Key_D) and not self.is_dead:
            if self.is_tree_at(current_grid_x + 1, self.player_y): return
            self.player_x = current_grid_x + 1
            self.log_event(f"Moved RIGHT. Grid X: {self.player_x}")

        self.update()
    def update_game_state(self):
        if getattr(self, 'is_waiting_for_players', False) or getattr(self, 'is_counting_down', False):
            self.update()
            return

        if self.is_replay_mode and not self.is_dead and not self.is_paused:
            while self.replay_index < len(self.recorded_inputs):
                tick, key = self.recorded_inputs[self.replay_index]
                if tick == self.current_tick:
                    event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
                    self.keyPressEvent(event, simulated=True)
                    self.replay_index += 1
                else:
                    break

        if not self.is_dead and not self.is_paused:
            self.current_tick += 1

        player_on_log = False
        current_lane_type = "grass"

        if not self.is_dead and not self.is_paused:
            self.camera_scroll += 0.01 + (self.difficulty * 1.5)
            if self.camera_scroll >= 1.0:
                self.camera_scroll -= 1.0
                self.player_y += 1
                self.shift_lanes_down()

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
                        if dist < 0: dist += 16
                        if dist < 4.0 and lane.objects[j].speed > front_car.speed:
                            lane.objects[j].speed = front_car.speed
                    else:
                        front_car = lane.objects[(j - 1) % num_cars]
                        dist = lane.objects[j].x_pos - front_car.x_pos
                        if dist < 0: dist += 16
                        if dist < 4.0 and lane.objects[j].speed > front_car.speed:
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
                        if obj.obj_type == "car" and not self.god_mode:
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

        if current_lane_type == "river" and not player_on_log and not self.god_mode:
            self.game_over()

        if (self.player_x < -1 or self.player_x > 9 or self.player_y > 15) and not self.god_mode:
            self.game_over()

        self.update()

    def get_lane(self, y):
        for lane in self.lanes:
            if lane.y_pos == y:
                return lane
        return None

    def ai_step(self):
        if not self.ai_mode or self.is_dead or self.is_paused or self.is_replay_mode:
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

                low_penalty = 0
                if ty > 10:
                    low_penalty = (ty - 10) * (10 + self.difficulty * 500)
                    if dy >= 0:
                        score -= low_penalty

                if ty >= 14:
                    score -= 300

                if dy == 1 and self.camera_scroll > 0.6:
                    score -= 150

                target_world_pos = (tx, self.absolute_y - dy)
                if target_world_pos in self.history_path:
                    visits = self.history_path.count(target_world_pos)
                    score -= (150 + low_penalty) * visits

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

                if self.stuck_ticks > 15:
                    if dx == 0 and dy == 0:
                        score -= 600
                    if dy == 1:
                        score += 300
                    if dx != 0:
                        score += 100

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

    def load_config(self):
        default_config = {
            "base_difficulty": 0.0,
            "base_spawn_rate": 0.3,
            "ai_tickrate": 30,
            "game_timer_ms": 30,
            "lane_weights": ["road", "river", "grass"],
            "max_trees": 4,
            "min_car_speed": 0.02,
            "max_car_speed": 0.10,
            "river_block": True
        }
        try:
            with open("config.json", "r") as f:
                data = json.load(f)

            self.config = {
                "base_difficulty": float(data.get("base_difficulty", 0.0)),
                "base_spawn_rate": float(data.get("base_spawn_rate", 0.3)),
                "ai_tickrate": max(1, int(data.get("ai_tickrate", 30))),
                "game_timer_ms": max(1, int(data.get("game_timer_ms", 30))),
                "lane_weights": data.get("lane_weights", ["road", "river", "grass"]),
                "max_trees": min(9, max(1, int(data.get("max_trees", 4)))),
                "min_car_speed": float(data.get("min_car_speed", 0.02)),
                "max_car_speed": float(data.get("max_car_speed", 0.10)),
                "river_block": bool(data.get("river_block", True))
            }
        except Exception:
            self.config = default_config

        self.river_block = self.config["river_block"]

        if hasattr(self, 'score'):
            self.difficulty = self.config["base_difficulty"] + (self.score * 0.0001)
            self.spawn_rate = min(self.config["base_spawn_rate"] + self.difficulty * 10, 0.95)

        if hasattr(self, 'ai_timer'):
            self.ai_timer.setInterval(self.config["ai_tickrate"])
        if hasattr(self, 'game_timer'):
            self.game_timer.setInterval(self.config["game_timer_ms"])

        if hasattr(self, 'score'):
            self.log_event("Config reloaded")

        self.update()


class LobbyMenu(QWidget):
    back = pyqtSignal()
    ready = pyqtSignal()
    unready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_ready = False
        self.is_locked = False
        self.setStyleSheet("""
            QWidget { background: transparent; }
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
            QPushButton:hover{ background-color: #c0392b; }
            QPushButton:disabled { background-color: #7f8c8d; }
            QLabel {
                color: rgb(255, 255, 255);
                font-family: Press Start 2P;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }
            QLabel#players_list { font-size: 14px; color: #f1c40f; }
        """)
        layout = QVBoxLayout()
        title = QLabel("Lobby", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.players_label = QLabel("Players:\n", self)
        self.players_label.setObjectName("players_list")
        self.players_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ready_btn = QPushButton("Ready (0/0)", self)
        self.ready_btn.setEnabled(False)
        self.back_btn = QPushButton("Disconnect", self)

        self.ready_btn.clicked.connect(self.on_ready_clicked)
        self.back_btn.clicked.connect(lambda: self.back.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.players_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.ready_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def update_lobby(self, players_str, ready_str):
        players = players_str.split(',')
        self.players_label.setText("Players:\n" + "\n".join(players))
        if self.is_locked:
            return
        if getattr(self, 'is_ready', False):
            self.ready_btn.setText(f"Unready ({ready_str})")
            self.ready_btn.setEnabled(True)
        else:
            self.ready_btn.setText(f"Ready ({ready_str})")
            self.ready_btn.setEnabled(len(players) > 1)

    def on_ready_clicked(self):
        if not hasattr(self, 'is_ready'):
            self.is_ready = False
        self.is_ready = not self.is_ready
        if self.is_ready:
            self.ready.emit()
        else:
            self.unready.emit()

    def lock_buttons(self):
        self.is_locked = True
        self.ready_btn.setEnabled(False)
        self.back_btn.setEnabled(False)

    def unlock_buttons(self):
        self.is_locked = False
        self.back_btn.setEnabled(True)
        self.ready_btn.setEnabled(True)

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
                background: transparent; 
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

        '''
        self.river_block_btn = QPushButton(" 2 River block", self)
        self.river_block_btn.setObjectName("toggle_btn")
        self.river_block_btn.setCheckable(True)
        self.river_block_btn.setChecked(True)
        self.river_block_btn.setIcon(toggle_icon)
        self.river_block_btn.setIconSize(QSize(32, 32))
        self.river_block_btn.toggled.connect(self.emit_river_block)
        '''

        self.apply_btn = QPushButton("Confirm settings", self)
        self.apply_btn.clicked.connect(self.apply_settings)

        self.back_btn = QPushButton("Back", self)
        self.back_btn.clicked.connect(lambda: self.back_to_menu.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.res_options, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.god_mode_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.debug_mode_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        # layout.addWidget(self.river_block_btn, alignment=Qt.AlignmentFlag.AlignCenter)
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


class SingleplayerMenu(QWidget):
    new_game = pyqtSignal()
    load_game = pyqtSignal()
    back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background: transparent; }
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
            QPushButton:hover{ background-color: #c0392b; }
            QLabel {
                color: rgb(255, 255, 255);
                font-family: Press Start 2P;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        layout = QVBoxLayout()
        title = QLabel("Singleplayer", self)

        self.new_game_btn = QPushButton("New Game", self)
        self.load_game_btn = QPushButton("Load Save", self)
        self.back_btn = QPushButton("Back", self)

        self.new_game_btn.clicked.connect(lambda: self.new_game.emit())
        self.load_game_btn.clicked.connect(lambda: self.load_game.emit())
        self.back_btn.clicked.connect(lambda: self.back.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.new_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.load_game_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)


class MultiplayerMenu(QWidget):
    back = pyqtSignal()
    join_game = pyqtSignal(str)  # Nowy sygnał wysyłający nick

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background: transparent; }
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
            QPushButton:hover{ background-color: #c0392b; }
            QLabel {
                color: rgb(255, 255, 255);
                font-family: Press Start 2P;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
            QLineEdit {
                background-color: white;
                color: black;
                border-radius: 12px;
                font-size: 16px;
                font-family: Press Start 2P;
                min-width: 230px;
                min-height: 55px;
                padding-left: 15px;
            }
        """)
        layout = QVBoxLayout()
        title = QLabel("Multiplayer", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.nickname_input = QLineEdit(self)
        self.nickname_input.setPlaceholderText("Nickname")
        self.nickname_input.setMaxLength(16)

        self.join_btn = QPushButton("Join Game", self)
        self.back_btn = QPushButton("Back", self)

        self.join_btn.clicked.connect(self.on_join_clicked)
        self.back_btn.clicked.connect(lambda: self.back.emit())

        layout.addStretch()
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)
        layout.addWidget(self.nickname_input, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.join_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def on_join_clicked(self):
        nickname = self.nickname_input.text().strip()
        if nickname:
            self.join_game.emit(nickname)

class Menu(QWidget):
    singleplayer = pyqtSignal()
    multiplayer = pyqtSignal()
    options = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
                    QWidget { background: transparent; }
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
                        background: transparent;
                    }
                    QLabel#author{
                        font-size: 12px;
                        font-weight: normal;
                        padding-bottom: 20px;
                    }
                """)
        menu_layout = QVBoxLayout()

        title = QLabel("Crossy Road", self)
        author = QLabel("Filip Pietrzak 198275", self)
        author.setObjectName("author")

        self.singleplayer_btn = QPushButton("Singleplayer", self)
        self.multiplayer_btn = QPushButton("Multiplayer", self)
        self.option_btn = QPushButton("Options", self)
        self.exit_btn = QPushButton("Exit", self)

        self.singleplayer_btn.clicked.connect(lambda: self.singleplayer.emit())
        self.multiplayer_btn.clicked.connect(lambda: self.multiplayer.emit())
        self.option_btn.clicked.connect(lambda: self.options.emit())
        self.exit_btn.clicked.connect(QApplication.instance().quit)

        menu_layout.addStretch()
        menu_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(author, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.singleplayer_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.multiplayer_btn, alignment=Qt.AlignmentFlag.AlignCenter)
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