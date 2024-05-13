# Tello Drone with gesture commands

This project will work only if you have Windows and WSL machine on your host system.

Installation guide:

- Copy this repository in preferred directory on Windows: `git clone git@github.com:MarkMinerov/Drone-gestures.git`
- Copy this repository once again in preferred directory on WSL: `git clone git@github.com:MarkMinerov/Drone-gestures.git`
- On WSL go to `drone-gesture/WSL` and download download [this archive](https://drive.google.com/file/d/1wkIOwe0POEK250BgHQ8TmdpK_onGVium/view?usp=sharing) and unzip it. You should have then folder with name `checkpoints` and two files inside of it. This files are needed to launch our model with pre-trained weights
- [Install conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) on your WSL
- [Install Tensorflow](https://docs.anaconda.com/anaconda/user-guide/tasks/tensorflow/) on your WSL
- You also need to install `object_detection` library, you can find installation process on the [following link](https://github.com/GBJim/object_detection/blob/master/g3doc/installation.md)
- On your Windows machine you have to install next packages: `cv2`, `numpy`
- Connect to your Tello drone via Wi-Fi
- open `proxy.py` and set `WSL_IP` variable value to your WSL machine's IP.
- Launch script `server.py` on WSL and wait until it stop logging
- Launch script `proxy.py` on Windows

Thus, you can use next gestures to control the drone:

- `palm`: `takeoff`
- `rock`: `land`
- `peace`: `left $DISTANCE`
- `three`: `right $DISTANCE`
- `stop`: `up $DISTANCE`
- `fist`: `down $DISTANCE`

You may specify value for `$DISTANCE` variable in `proxy.py` script.
