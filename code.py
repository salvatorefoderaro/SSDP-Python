import sys
from ssdp import Server, Client, Nat
from ssdp import gen_logger
from queue import Queue

logger = gen_logger('sample')

if __name__ == '__main__':
    try:
        if sys.argv[1] == 'server':
            upnpServer  = Server(9001, 'blockchain', 'main1111')
            upnpServer.run()
        elif sys.argv[1] == 'client':
            queue = Queue()
            upnpClient = Client('blockchain', 'main1111', queue)
            upnpClient.start()
            logger.info(queue.get())
        elif sys.argv[1] == 'nat':
            nat = Nat()
            print(nat.addPortForward(8011, 8015))
        else:
            logger.warning('need params server or clinet')
    except Exception as e:
        logger.error(e)
