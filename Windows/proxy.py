import socket
import numpy as np
import cv2
import threading
import queue
import winsound

WSL_IP = '192.168.69.132'

# Create a UDP socket
proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
LOCAL_ADDRESS = ("", 5555)
TELLO_CAMERA_ADDRESS = "udp://0.0.0.0:11111"
TELLO_COMMAND_ADDRESS = ('192.168.10.1', 8889)
CAST_IP = (WSL_IP, 5001)
COMMANDS_WSL_ADDRESS = (WSL_IP, 8086)

RESPONSE_SIZE = 2048
bufferSize = 4096
capture = None

# listen to a a TCP socket
TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket.connect(COMMANDS_WSL_ADDRESS)

DISTANCE = 30

COMMANDS = {
  "palm": "takeoff",
  "rock": "land",
  'peace': f"left {DISTANCE}",
  'three': f"right {DISTANCE}",
  'stop': f"up {DISTANCE}",
  'fist': f"down {DISTANCE}"
}

def handle_commands(socket_queue, socket):
  while True:
    data = socket.recv(1024)
    if not data: break
    socket_queue.put(data.decode())

socket_queue = queue.Queue()

t = threading.Thread(target=handle_commands, args=(socket_queue, TCP_socket), daemon=True)
t.start()

def send_command(socket, command, address):
  print(f"Sending command '{command}' to Tello...")
  socket.sendto(command.encode(), address)
  response, _ = socket.recvfrom(RESPONSE_SIZE)

  return response

def main():
  global capture

  # start SDK socket
  with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as command_socket:
    command_socket.bind(LOCAL_ADDRESS)
    response = send_command(command_socket, "command", TELLO_COMMAND_ADDRESS) # init SDK

    while response != b'ok':
      print("Trying again init SDK...")
      response = send_command(command_socket, "command", TELLO_COMMAND_ADDRESS) # try to re-init sdk again SDK

    print("SDK answered with OK status...")
    response = send_command(command_socket, "streamon", TELLO_COMMAND_ADDRESS) # start streaming

    if response == b'ok':
      print("Stream request answered with OK status, starting stream...")

      try:
        # read stream stream from Tello
        capture = cv2.VideoCapture(TELLO_CAMERA_ADDRESS, cv2.CAP_FFMPEG)

        if not capture.isOpened(): capture.open(TELLO_CAMERA_ADDRESS)

        while True:
          _, frame = capture.read()
          img_encode = cv2.imencode('.jpg', frame)[1]
          data_encode = np.array(img_encode)
          bytes_encoded = data_encode.tobytes()
          chunk_pos = 0

          while chunk_pos < len(bytes_encoded):
            proxy_socket.sendto(bytes_encoded[chunk_pos:min(chunk_pos + bufferSize, len(bytes_encoded))], CAST_IP)
            chunk_pos += bufferSize

            try:
              result = socket_queue.get_nowait()

              if result == 'pending':
                winsound.PlaySound('./sounds/pending.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
              else:
                winsound.PlaySound('./sounds/done.wav', winsound.SND_FILENAME | winsound.SND_ASYNC)
                send_command(command_socket, COMMANDS[result], TELLO_COMMAND_ADDRESS)

            except queue.Empty: pass

      except KeyboardInterrupt:
        capture.release()
        response = send_command(command_socket, "streamoff", TELLO_COMMAND_ADDRESS)
        print("See you later! Bye!")

main()