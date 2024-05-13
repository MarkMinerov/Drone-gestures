import socket
import numpy as np
import cv2
import threading
import queue

WSL_IP = '192.168.69.132'

# Create a UDP socket
proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
TELLO_COMMAND_ADDRESS = ('localhost', 41234)
CAST_IP = (WSL_IP, 5001)
COMMANDS_WSL_ADDRESS = (WSL_IP, 8086)
LOCAL_ADDRESS = ("", 5555)

RESPONSE_SIZE = 2048
bufferSize = 4096
capture = None

# listen to a a TCP socket
TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket.connect(COMMANDS_WSL_ADDRESS)

DS = {
    "palm": "takeoff",
    "rock": "land",
    'peace': "left",
    "like": "forward",
    "dislike": "back"
    # 'three': "right {DISTANCE}",
    # 'stop': "up {DISTANCE}",
    # 'fist': "down {DISTANCE}",
    # "two_up": "cw {DISTANCE}",
    # "ok": "ccw {DISTANCE}",
    # "call": "flip l",

}


def handle_commands(socket_queue, socket):
    while True:
        data = socket.recv(1024)
        if not data:
            break
        socket_queue.put(data.decode())


socket_queue = queue.Queue()

t = threading.Thread(
    target=handle_commands,
    args=(socket_queue, TCP_socket),
    daemon=True
)

t.start()

cam = cv2.VideoCapture(0)
cv2.namedWindow('Named Window')


def send_command(socket, command, address):
    print(f"Sending command '{command}' to the Drone...")
    socket.sendto(command.encode(), address)


def main():
    global capture

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as command_socket:
        command_socket.bind(LOCAL_ADDRESS)
        try:
            while True:
                ret, frame = cam.read()
                if not ret:
                    break
                cv2.imshow('Named Window', frame)
                cv2.waitKey(1)
                img_encode = cv2.imencode('.jpg', frame)[1]
                data_encode = np.array(img_encode)
                bytes_encoded = data_encode.tobytes()
                chunk_pos = 0

                while chunk_pos < len(bytes_encoded):
                    proxy_socket.sendto(
                        bytes_encoded[chunk_pos:min(
                            chunk_pos + bufferSize, len(bytes_encoded))],
                        CAST_IP)
                    chunk_pos += bufferSize

                try:
                    result = socket_queue.get_nowait()
                    print(DS[result])
                    send_command(command_socket,
                                 DS[result], TELLO_COMMAND_ADDRESS)
                except queue.Empty:
                    pass

        except queue.Empty:
            pass


main()
