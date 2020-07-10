from ssdp_util import gen_logger, get_local_IP
import os
import socket
import re
import sys
import time
import threading

logger = gen_logger('upnp')
  
class Server(threading.Thread):

    BCAST_IP = '239.255.255.250'
    UPNP_PORT = 10000
    IP = '0.0.0.0'
    M_SEARCH_REQ_MATCH = "M-SEARCH"
    
    def __init__(self, port, protocal, networkid):
        '''
        port: a blockchain network port to broadcast to others
        '''
        threading.Thread.__init__(self)
        self.interrupted = False
        self.port = port
        self.protocol = protocal
        self.networkid = networkid
        return
    
    def run(self):
        self.listen()
    
    def stop(self):
        self.interrupted = True
        logger.info("upnp server stop")
    
    def listen(self):
        '''
        Listen on broadcast addr with standard 1900 port
        It will reponse a standard ssdp message with blockchain ip and port info if receive a M_SEARCH message
        '''
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.BCAST_IP) + socket.inet_aton(self.IP))
            sock.bind((self.IP, self.UPNP_PORT))
            sock.settimeout(1)
            logger.info("upnp server is listening...")
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    logger.info("IP Addres of the node is: %s", addr)
                    self.respond(addr)
                except socket.error:
                    if self.interrupted:
                        sock.close()
                        return
                    
        except Exception as e:
            logger.info('Error in npnp server listening: %s', e)

    def respond(self, addr):
        try:
            local_ip = get_local_IP()
            UPNP_RESPOND = """HTTP/1.1 200 OK
            CACHE-CONTROL: max-age=1800
            ST: private blockchain upnp 1.0
            EXT:
            LOCATION: {}_{}://{}:{}
            """.format(self.protocol, self.networkid, local_ip, self.port).replace("\n", "\r\n")
            outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            outSock.sendto(UPNP_RESPOND.encode('ASCII'), addr)
            logger.debug('response data: %s', UPNP_RESPOND)
            outSock.close()
        except Exception as e:
            logger.error('Error in upnp response message to client %s', e)


class Client(threading.Thread):

    # 30 seconds for search_interval
    SEARCH_INTERVAL = 5
    BCAST_IP = '239.255.255.250'
    BCAST_PORT = 10000

    def __init__(self, protocol, networkid, queue):
        threading.Thread.__init__(self)
        self.interrupted = False
        self.protocol = protocol
        self.networkid = networkid
        self.queue = queue
    
    def run(self):
        self.keep_search()
    
    def stop(self):
        self.interrupted = True
        logger.info("upnp client stop")

    def keep_search(self):
        '''
        run search function every SEARCH_INTERVAL
        '''
        try:
            while True:
                self.search()
                for x in range(self.SEARCH_INTERVAL):
                    time.sleep(1)
                    if self.interrupted:
                        return
        except Exception as e:
            logger.error('Error in upnp client keep search %s', e)

    def search(self):
        '''
        broadcast SSDP DISCOVER message to LAN network
        filter our protocal and add to network
        '''
        try:
            SSDP_DISCOVER = ('M-SEARCH * HTTP/1.1\r\n' +
                            'HOST: 239.255.255.250:1900\r\n' +
                            'MAN: "ssdp:discover"\r\n' +
                            'MX: 1\r\n' +
                            'ST: ssdp:all\r\n' +
                            '\r\n')
            LOCATION_REGEX = re.compile("LOCATION: {}_{}://[ ]*(.+)\r\n".format(self.protocol, self.networkid), re.IGNORECASE)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(SSDP_DISCOVER.encode('ASCII'), (self.BCAST_IP, self.BCAST_PORT))
            sock.settimeout(3)
            while True:
                data, addr = sock.recvfrom(1024)
                logger.info('Reply from the server. IP Addres is: %s', addr)
                location_result = LOCATION_REGEX.search(data.decode('ASCII'))
                if location_result:
                    peer_ip, peer_port = location_result.group(1).split(":")
                    # logger.info('{}:{} is running the same protocal'.format(peer_ip, peer_port))
                    self.queue.put((peer_ip, peer_port))
        except:
            sock.close()