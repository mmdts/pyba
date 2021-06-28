#!/bin/bash
echo "Please make sure both cuda 11.3 and conda are available before running this script."
echo "By downloading and using the CUDA Toolkit conda packages, you accept the terms and conditions of"
echo "the CUDA End User License Agreement (EULA): https://docs.nvidia.com/cuda/eula/index.html"
echo ""
echo "The minified javascript external library files (not part of this codebase) are downloaded using wget"
echo "from CDN sites. If you do not wish to use such sites, please find your own copies of the minified files."
conda create -n pyba
conda install gevent gevent-websocket flask flask-socketio colorama
conda install pytorch torchvision torchaudio   cudatoolkit=11.1 -c pytorch -c nvidia
# wget .min.js files

# create run script
