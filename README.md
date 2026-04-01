# Crossy Road (PyQt6 Edition)

Desktop clone of the popular arcade game Crossy Road, developed in Python using the **PyQt6** framework. The player controls a character attempting to cross endless roads, rivers, and grass fields while avoiding obstacles and managing a dynamic camera.

## About the Project

Crossy Road PyQt6 is a functional arcade game featuring:
- **Procedural Generation**: Levels and lane types are generated randomly in real-time, ensuring a unique experience for every playthrough.
- **Save & Load System**: Players can save their current progress (score, position, and seed) to a JSON file and resume their game later.
- **AI Bot Mode**: Integrated AI agent that uses a risk-assessment scoring algorithm to navigate through traffic and rivers automatically.
- **Replay Mode**: After a game over, players can watch a frame-by-frame replay of their last attempt based on recorded inputs.

## Technologies

- **Python** 3.8+ - core logic
- **PyQt6** - GUI and rendering engine
- **JSON** - configuration and save game management
- **QTimer** - game loop and AI tickrate control

## Installation and Running

Install the required library:
```bash
pip install PyQt6
```

Run the game:
```bash
python main.py
```

## Advanced Options

- **Resolution Scaling**: Support for multiple window sizes and a dedicated Fullscreen mode.
- **God Mode**: Optional invincibility for testing or casual play.
- **Debug Mode**: Real-time visualization of hitboxes, object speeds, difficulty scaling, and the current random seed.
- **Dynamic Difficulty**: Game scales movement speed and object spawn rates based on the player's current score.

## License

Educational project - Filip Pietrzak
