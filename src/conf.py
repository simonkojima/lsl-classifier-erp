import os
import sys
import socket

from toeplitzlda.classification import ShrinkageLinearDiscriminantAnalysis, ToeplitzLDA

home_dir = os.path.expanduser('~')
pyerp_dir = os.path.join(home_dir, "git", "pyerp", "src")
sys.path.append(pyerp_dir)

import pyerp

ip_address = socket.gethostbyname(socket.gethostname())
port = 49154
length_header = 64
length_chunk = 2**12

log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-classifier-erp")

event_id = dict()
event_id['nontarget'] = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
event_id['target'] = ['101', '102', '103', '104', '105', '106', '107', '108', '109', '110', '111', '112', '113', '114', '115'] 

event_id_online = event_id['nontarget'] + event_id['target']

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

clf = ShrinkageLinearDiscriminantAnalysis(n_channels=9)
vectorizer = pyerp.EpochsVectorizer(ivals = ivals, type = 'ndarray', tmin = tmin, tmax = tmax, include_tmax = True, fs = fs)