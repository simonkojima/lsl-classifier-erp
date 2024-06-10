import os
import sys
import socket

from toeplitzlda.classification import ShrinkageLinearDiscriminantAnalysis, ToeplitzLDA

home_dir = os.path.expanduser('~')
pyerp_dir = os.path.join(home_dir, "git", "pyerp", "src")
sys.path.append(pyerp_dir)

import pyerp

default_ip_address = socket.gethostbyname(socket.gethostname())
default_port = 49154

length_header = 64
#length_chunk = 2**12

client_name = "main"

log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-classifier-erp")

event_id = dict()
event_id['nontarget'] = [str(val) for val in range(1, 31)]
event_id['target'] = [str(val) for val in range(101, 131)] 

event_id_online = event_id['nontarget']

ivals = [[0.0, 0.1],
         [0.1, 0.2],
         [0.2, 0.3],
         [0.3, 0.4],
         [0.4, 0.5],
         [0.5, 0.6],
         [0.6, 0.7],
         [0.7, 0.8],
         [0.8, 0.9],
         [0.9, 1.0]]

fs = 1000
tmin = -0.1
tmax = 1.0
baseline = None

clf = ShrinkageLinearDiscriminantAnalysis(n_channels=9)
vectorizer = pyerp.EpochsVectorizer(ivals = ivals, type = 'ndarray', tmin = tmin, tmax = tmax, include_tmax = True, fs = fs)

# for extracting epochs
# used in -> main.py, extract_epochs()
filter_range = [1, 40]
filter_order = 2
name_eeg_stream = 'jarvis-erp'
name_marker_stream = 'scab-c'
