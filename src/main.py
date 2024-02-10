import os
import logging
import socket
import datetime
import json
import traceback

from utils.std import mkdir
from utils import log

def recv_sock_split(conn, msg_length, chunk_length):
    msg = list()
    for m in range(int(msg_length/chunk_length) + 2):
        msg.append(conn.recv(chunk_length).decode('utf-8'))
    return "".join(msg)[0:msg_length]

def main(ip_address,
         port,
         length_header,
         length_chunk):
    
    logger = logging.getLogger(__name__)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip_address, port))
    print("server info. ip: %s, port: %s"%(str(ip_address), str(port)))
    
    server.settimeout(10)
    server.listen()
    conn, addr = server.accept()
    logger.debug("New socket connection was established. '%s'"%str(addr))
    
    print("here")
    msg_length = int.from_bytes(conn.recv(length_header), 'little')
    print(msg_length)

    """
    msg = list()
    for m in range(int(msg_length/sock_split)+1):
        msg.append(conn.recv(sock_split).decode('utf-8'))
     
    flag = False
    print(len("".join(msg)))
    print("".join(msg)[0:100])
    """
    msg = recv_sock_split(conn, msg_length, length_chunk)

    #msg_json = json.loads("".join(msg)[0:msg_length])
    msg_json = json.loads(msg)
    print(msg_json.keys())
    """
    #conn.settimeout(5)
    flag = True
    while flag:
        try:

        except socket.timeout as e:
            pass
        except KeyboardInterrupt as e:
            break
        except Exception as e:
            logger.debug(traceback.format_exc())
    """
        


if __name__ == "__main__":

    import conf
    log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-epoching")

    log_strftime = "%y-%m-%d"
    datestr =  datetime.datetime.now().strftime(log_strftime) 
    log_fname = "%s.log"%datestr
    
    print(log_dir)

    mkdir(log_dir)
    if os.path.exists(os.path.join(conf.log_dir, log_fname)):
        os.remove(os.path.join(conf.log_dir, log_fname))
    log.set_logger(os.path.join(log_dir, log_fname), True)
    
    logger = logging.getLogger(__name__)
    logger.debug("ip address: %s"%str(conf.ip_address))
    logger.debug("port: %s"%str(conf.port))
    
    main(conf.ip_address,
         conf.port,
         conf.length_header,
         conf.length_chunk)
