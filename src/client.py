import os
import sys
import traceback

import socket
import json

sys.path.append(os.path.join(os.path.expanduser('~'), "git", "pyerp", "src"))
import pyerp
import conf

import numpy as np

def send_sock_split(conn, msg_length, chunk_length, data):
    for m in range(int(msg_length/chunk_length)):
        val = data[(m*chunk_length):((chunk_length*(m+1)))]
        conn.send(val)
    print(m)
    conn.send(data[((m+1)*chunk_length):len(data)])

if __name__ == "__main__":
    with open("epochs.json", 'r') as f:
        data = json.load(f)
        
    print(data.keys())

    print(len(data['epochs']))
    epochs = list()
    for mat in data['epochs']:
        epochs += mat
    print(len(epochs))

    import conf
    vectorizer = conf.vectorizer

    vec = vectorizer.transform(np.array(epochs))

    events = list()
    for val in data['events']:
        events += val
    print(events)
    print(len(events))

    SERVER = socket.gethostbyname(socket.gethostname())
    IPADDR = "127.0.0.1"
    IPADDR = SERVER
    PORT = 49155
    header = 64
    #FORMAT = ''

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #conn.settimeout(120)
    conn.connect((IPADDR, PORT))
    print("connected.")

    """
    conns_send(conns, len(json.dumps(json_data).encode('utf-8')).to_bytes(length_header, byteorder='little'))
    conns_send(conns, json.dumps(json_data).encode('utf-8'))


    msg_length = int.from_bytes(cl.recv(header), 'little')
    msg = cl.recv(msg_length).decode('utf-8')
    msg_json = json.loads(msg)
    """
    
    
    # train classifier
    input("press any key")
    msg = dict()
    msg['type'] = 'cmd'
    msg['cmd'] = 'train'

    data = json.dumps(msg).encode('utf-8')
    msg_length = len(data)
    conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
    conn.send(data)

    msg = dict()
    msg['epochs'] = epochs
    msg['events'] = events

    data = json.dumps(msg).encode('utf-8')
    msg_length = len(data)
    conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
    send_sock_split(conn, msg_length, conf.length_chunk, data)
    
    # training end

    msg_length = int.from_bytes(conn.recv(conf.length_header), 'little')
    msg_json = conn.recv(msg_length).decode('utf-8')
    msg_json = json.loads(msg_json)
    
    
    if msg_json['type'] == 'info':
        if msg_json['info'] == 'training_completed':
           pass 
       
    print(msg_json)
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
            data = json.dumps(msg).encode('utf-8')
            msg_length = len(data)
            conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
            conn.send(data)
            
            for idx in range(0, len(epochs)-1, 2):
                msg = dict()
                msg['type'] = 'epochs'
                data = json.dumps(msg).encode('utf-8')
                msg_length = len(data)
                conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
                conn.send(data)
                
                print(idx)
                data = [epochs[idx], epochs[idx + 1]]
                event = [events[idx], events[idx+1]]
                msg = dict()
                msg['epochs'] = data
                msg['events'] = event
                print(np.array(data).shape)
                data = json.dumps(msg).encode('utf-8')
                msg_length = len(data)
                conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
                send_sock_split(conn, msg_length, conf.length_chunk, data)
                #conn.send(data)
            
            msg = dict()
            msg['type'] = 'cmd'
            msg['cmd'] = 'trial-end'
            data = json.dumps(msg).encode('utf-8')
            msg_length = len(data)
            conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
            conn.send(data)

            msg_length = int.from_bytes(conn.recv(conf.length_header), 'little')
            msg_json = conn.recv(msg_length).decode('utf-8')
            msg_json = json.loads(msg_json)
            
            
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

    conn.close()
        
    exit()