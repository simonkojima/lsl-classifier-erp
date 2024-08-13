import os
import sys
import traceback

import socket
import json

import pyicom as icom

#sys.path.append(os.path.join(os.path.expanduser('~'), "git", "pyerp", "src"))
#import pyerp
import numpy as np
import pyxdf
import scipy

from utils.signal import apply_sosfilter, get_raw_from_streams

import mne

def train(client):

    # train classifier
    input("press any key")
    msg = dict()
    msg['type'] = 'cmd'
    msg['cmd'] = 'train'
    msg['files'] = [os.path.join(os.path.expanduser('~'),
                                "Documents",
                                "eeg",
                                "asme-speller",
                                "sub-P99",
                                "ses-S001",
                                "eeg",
                                "sub-P99_ses-S001_task-asme-offline_run-001_eeg.xdf")]
    msg['files'].append(msg['files'][0])
    #msg['events'] = events

    client.send(json.dumps(msg).encode('utf-8'))
    #print(len(json.dumps(msg).encode('utf-8')))
    
    # training end

    data = client.recv()
    msg_json = json.loads(data.decode('utf-8'))
    
    if msg_json['type'] == 'info':
        if msg_json['info'] == 'training_completed':
           pass 
       
    print("training was completed")

def trial(client):
    
    with open("sub-P99_epochs_training_task-asme_run-1_trial-1.json", "r") as f:
    	data = json.load(f)

    epochs = data['epochs']
    events = data['events']

    flag = [True]
    while flag[0]:
        #input("Press Any Key to Continue.")
        try:

            input("press any key")
            
            # start trial
            msg = dict()
            msg['type'] = 'cmd'
            msg['cmd'] = 'trial-start'
            client.send(json.dumps(msg).encode('utf-8'))
            
            for idx in range(0, len(epochs)):
                data = epochs[idx]
                event = events[idx]

                msg = dict()
                msg['type'] = 'epochs'
                msg['epochs'] = data
                msg['events'] = event
                
                #print(msg)

                client.send(json.dumps(msg).encode('utf-8'))
                
                import time
                time.sleep(0.2)
                
                
            
            msg = dict()
            msg['type'] = 'cmd'
            msg['cmd'] = 'trial-end'
            client.send(json.dumps(msg).encode('utf-8'))

            data = client.recv()
            msg_json = json.loads(data.decode('utf-8'))
            
            if msg_json['type'] == 'info':
                if msg_json['info'] == 'classification_result':
                    print("output: %s"%str(msg_json['output']))
                    print("pred: %s"%str(msg_json['pred']))

        except socket.timeout as e:
            pass
        except KeyboardInterrupt as e:
            flag[0] = False
        except Exception as e:
            print(traceback.format_exc())
            flag[0] = False

    client.close()
        
if __name__ == "__main__":

    ip = "localhost"
    port = 49154

    client = icom.client(ip = ip,
                         port = port)
    client.connect()

    print("connected.")
    
    train(client)
    input("Press Any Key to Continue to start trial")
    trial(client)