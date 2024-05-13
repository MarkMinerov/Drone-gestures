import socket
import numpy as np
from PIL import Image
import io
import pathlib

import os
import tensorflow as tf
from object_detection.utils import config_util
from object_detection.builders import model_builder
from object_detection.utils import label_map_util

COMMAND_THRESHOLD = 1
COMMANDS_WSL_ADDRESS = ('0.0.0.0', 8086)
VIDEO_PROXY_ADDRESS = ('0.0.0.0', 5001)
BUFFER_SIZE = 4096

# Hook up Tensorflow and Neural Network
filenames = list(pathlib.Path('checkpoints').glob('*.index'))
filenames.sort()

configs = config_util.get_configs_from_pipeline_file("data/pipeline.config")

label_map_path = configs['eval_input_config'].label_map_path
label_map = label_map_util.load_labelmap(label_map_path)

categories = label_map_util.convert_label_map_to_categories(
  label_map,
  max_num_classes=label_map_util.get_max_label_map_index(label_map),
  use_display_name=True
)

category_index = label_map_util.create_category_index(categories)
label_map_dict = label_map_util.get_label_map_dict(label_map, use_display_name=True)

model_config = configs['model']
detection_model = model_builder.build(model_config=model_config, is_training=False)

# Restore checkpoint
ckpt = tf.compat.v2.train.Checkpoint(model=detection_model)
ckpt.restore(os.path.join(str(filenames[-1]).replace('.index','')))

def get_model_detection_function(model):
  """Get a tf.function for detection."""

  @tf.function
  def detect_fn(image):
    """Detect objects in image."""

    image, shapes = model.preprocess(image)
    prediction_dict = model.predict(image, shapes)
    detections = model.postprocess(prediction_dict, shapes)

    return detections, prediction_dict, tf.reshape(shapes, [-1])

  return detect_fn

detect_fn = get_model_detection_function(detection_model)
label_id_offset = 1

# Process sockets
executing_command = None
request_streak = { "name": "", "row": 0 }
pending_command_threshold_max_error = 0

def process_request(request):
    command_to_execute = None
    global executing_command, request_streak, pending_command_threshold_max_error

    # if no command is provided
    if executing_command == None:
        if request_streak["name"] == request:
            request_streak['row'] += 1
        else:
            request_streak["name"] = request
            request_streak["row"] = 0

        if request_streak["row"] >= COMMAND_THRESHOLD:
            command_to_execute = request_streak["name"]
            request_streak = { "name": "", "row": 0 }

    return command_to_execute

# Create socket to send commands back to proxy
TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
TCP_socket.bind(COMMANDS_WSL_ADDRESS)
TCP_socket.listen(1)

proxy_conn, addr = TCP_socket.accept()
print('Connected by', addr)

# Create a UDP socket to read video stream
proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to a specific IP address and port
proxy_socket.bind(VIDEO_PROXY_ADDRESS)

filenames = list(pathlib.Path('checkpoints').glob('*.index'))
filenames.sort()

def is_image_corrupted(udp_stream):
    byte_stream = io.BytesIO(udp_stream)
    try:
        img = Image.open(byte_stream)
        img.load()
        return False
    except:
        return True

print("ready to accept frames")

try:
    while True:
        frame = b''

        while True:
            data, address = proxy_socket.recvfrom(BUFFER_SIZE)
            frame += data

            if len(data) < BUFFER_SIZE: break

        if frame.startswith(b'\xff\xd8') and not is_image_corrupted(frame):
            byte_stream = io.BytesIO(frame)
            img = Image.open(byte_stream)
            image_np = np.array(img)

            input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)
            detections, predictions_dict, shapes = detect_fn(input_tensor)

            best_detection_index = detections['detection_scores'][0].numpy().argmax()
            detections_class = (detections['detection_classes'][0].numpy() + label_id_offset).astype(int)[best_detection_index]

            if detections['detection_scores'][0].numpy().max() > .5:
                print(category_index[detections_class]['name'])
                command_to_execute = process_request(category_index[detections_class]['name'])

                if command_to_execute:
                    proxy_conn.sendall(command_to_execute.encode('utf-8'))

        frame = b''

except KeyboardInterrupt:
    print("Finishing execution... Pa-pa!")