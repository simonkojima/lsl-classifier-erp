import os
import sys
import traceback

import socket
import json

import pyicom as icom

sys.path.append(os.path.join(os.path.expanduser('~'), "git", "pyerp", "src"))
import pyerp
import conf
import numpy as np

if __name__ == "__main__":
    with open("epochs.json", 'r') as f:
        data = json.load(f)

    epochs = list()
    for mat in data['epochs']:
        epochs += mat

    events = list()
    for val in data['events']:
        events += val

    ip = socket.gethostbyname(socket.gethostname())
    port = 49155

    client = icom.client(ip = ip,
                         port = port,
                         name = conf.client_name)
    client.connect()

    print("connected.")
    
    
    # train classifier
    input("press any key")
    msg = dict()
    msg['type'] = 'cmd'
    msg['cmd'] = 'train'
    msg['epochs'] = epochs
    msg['events'] = events

    client.send(json.dumps(msg).encode('utf-8'))
    
    # training end

    data = client.recv()
    msg_json = json.loads(data.decode('utf-8'))
    
    if msg_json['type'] == 'info':
        if msg_json['info'] == 'training_completed':
           pass 
       
    print("training was completed")


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

            with open("epochs_online.json", 'r') as f:
                data = json.load(f)

            epochs = list()
            for mat in data['epochs']:
                epochs += mat

            events = list()
            for val in data['events']:
                events += val
            
            for idx in range(0, len(epochs)-1, 2):
                data = [epochs[idx], epochs[idx + 1]]
                event = [events[idx], events[idx+1]]

                msg = dict()
                msg['type'] = 'epochs'
                msg['epochs'] = data
                msg['events'] = event

                client.send(json.dumps(msg).encode('utf-8'))
                
            
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
        
    exit()