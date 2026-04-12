import socket
import threading
import time

HOST = '127.0.0.1'
PORT = 5555
clients = []
game_state = "LOBBY"


class User:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.username = None
        self.is_ready = False


def broadcast(msg):
    encoded = (msg + '\n').encode('utf-8')
    for c in clients.copy():
        try:
            c.conn.send(encoded)
        except:
            clients.remove(c)


def broadcast_lobby():
    if game_state != "LOBBY":
        return
    ready_count = sum(1 for c in clients if c.is_ready)
    total = len(clients)
    names = ",".join([c.username for c in clients if c.username])
    broadcast(f"LOBBY:{names}|READY:{ready_count}/{total}")


def start_countdown():
    global game_state
    game_state = "COUNTDOWN"
    print("Rozpoczynamy odliczanie...", flush=True)
    for i in [3, 2, 1]:
        print(f"Odliczanie: {i}", flush=True)
        broadcast(f"COUNTDOWN:{i}")
        time.sleep(1)
    game_state = "PLAYING"
    for c in clients:
        c.is_ready = False
    print("Gra wystartowala!", flush=True)
    broadcast("START")


def handle_client(user):
    global game_state
    buffer = ""
    while True:
        try:
            msg = user.conn.recv(1024)
            if not msg:
                break
            buffer += msg.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                if user.username is None:
                    base_name = line
                    new_name = base_name
                    counter = 0
                    current_usernames = [c.username for c in clients if c.username]

                    while new_name in current_usernames:
                        new_name = f"{base_name}{counter}"
                        counter += 1

                    user.username = new_name
                    user.conn.send((f"NAME_ACCEPTED:{user.username}\n").encode('utf-8'))
                    print(f"Gracz dolaczyl z nickiem: {user.username}", flush=True)

                    if game_state != "LOBBY":
                        ready_count = sum(1 for c in clients if c.is_ready)
                        total = len(clients)
                        names = ",".join([c.username for c in clients if c.username])
                        user.conn.send((f"LOBBY:{names}|READY:{ready_count}/{total}\n").encode('utf-8'))
                    else:
                        broadcast_lobby()
                elif line == "READY":
                    if game_state == "LOBBY":
                        user.is_ready = True
                        print(f"Gracz {user.username} jest gotowy.", flush=True)
                        broadcast_lobby()
                        if len(clients) > 1 and all(c.is_ready for c in clients if c.username):
                            threading.Thread(target=start_countdown, daemon=True).start()
                elif line == "UNREADY":
                    if game_state == "LOBBY":
                        user.is_ready = False
                        print(f"Gracz {user.username} odznaczyl gotowosc.", flush=True)
                        broadcast_lobby()
                elif line == "REMATCH":
                    user.is_ready = True
                    ready_count = sum(1 for c in clients if c.is_ready)
                    total = len(clients)
                    broadcast(f"REMATCH_UPDATE:{ready_count}/{total}")
                    print(f"Gracz {user.username} jest gotowy na rewanz ({ready_count}/{total}).", flush=True)
                    if len(clients) > 1 and all(c.is_ready for c in clients if c.username):
                        threading.Thread(target=start_countdown, daemon=True).start()
                else:
                    if game_state in ["PLAYING", "COUNTDOWN"]:
                        if "STATE" in line:
                            print(f"[{user.username}]: {line}", flush=True)
                        broadcast(f"[{user.username}]: {line}")
        except:
            break

    print(f"Gracz {user.username if user.username else user.addr} opuscil gre.", flush=True)
    if user in clients:
        clients.remove(user)

    if len(clients) < 2 and game_state != "LOBBY":
        game_state = "LOBBY"
        for c in clients:
            c.is_ready = False

    broadcast_lobby()
    user.conn.close()


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Serwer wystartowal na {HOST}:{PORT}", flush=True)
    while True:
        conn, addr = server.accept()
        new_client = User(conn, addr)
        clients.append(new_client)
        threading.Thread(target=handle_client, args=(new_client,), daemon=True).start()


if __name__ == "__main__":
    start_server()