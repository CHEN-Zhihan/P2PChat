from threading import Thread, Condition
from queue import Queue
import socket


KEEP_ALIVE = "KEEP_ALIVE"
CONNECT = "CONNECT"


def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


class Member(object):
    def __init__(self, name, ip, port, msgID=0):
        self._name = name
        self._ip = ip
        self._port = port
        self._msgID = msgID
        self._ID = sdbm_hash("{}{}{}".format(name, ip, port))

    def getID(self):
        return self._ID

    def getName(self):
        return self._name

    def getHost(self):
        return (self._ip, self._port)

    def __str__(self):
        return "{}@{}".format(self._name, self.getHost())

    def setMsgID(self, msgID):
        self._msgID = msgID


class AliveKeeper(Thread):
    """
    A seprate thread for KEEPALIVE
    """
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True
        self._condition = Condition()

    def run(self):
        while self._running:
            self._condition.acquire()
            self._condition.wait(20)
            self._condition.release()
            if self._running:
                self._manager.submit((KEEP_ALIVE, ))

    def shutdown(self):
        self._running = False
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()
        self.join()


class ConnectionKeeper(Thread):
    """
    Keep connected
    """
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._condition = Condition()
        self._sleep = Condition()
        self._running = True

    def run(self):
        while self._running:
            self._condition.acquire()
            self._condition.wait()
            self._condition.release()
            if self._running:
                self._sleep.acquire()
                self._sleep.wait(timeout=20)
                self._sleep.release()
                if self._running:
                    self._manager.submit((CONNECT, ))

    def schedule(self):
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()

    def shutdown(self):
        self._running = False
        self.schedule()
        self._sleep.acquire()
        self._sleep.notify()
        self._sleep.release()
        self.join()


class PeerListener(Thread):
    """
    Listen connection requests from peers
    """
    def __init__(self, manager, localhost):
        Thread.__init__(self)
        self._manager = manager
        self._soc = socket.socket()
        self._soc.bind(localhost)
        self._soc.listen(5)
        self._running = True

    def run(self):
        while self._running:
            try:
                print("[Peer Listener] Waiting for connection...")
                new, address = self._soc.accept()
            except OSError:
                if not self._running:
                    break
            else:
                if self._running:
                    self._manager.submit((NEW_CONNECTION, new))

    def shutdown(self):
        self._running = False
        self._soc.shutdown(socket.SHUT_RDWR)
        self._soc.close()
        self.join()


class PeerHandler(Thread):
    """
    Handle message sent from peers
    """
    def __init__(self, manager, ID, soc):
        Thread.__init__(self)
        self._manager = manager
        self._ID = ID
        self._running = True
        self._soc = soc

    def run(self):
        while self._running:
            msg = self._soc.recv(1024).decode("ascii")
            if self._running:
                if len(msg) != 0:
                    print("[Peer Received] {} *{}* ".format(
                        self._soc.getpeername(), msg
                    ))
                    self._manager.submit((RECEIVE_MESSAGE, msg, self))
                else:
                    print("[Peer Received] receive disconnect request\
                           from {}".format(
                        self._soc.getpeername()
                    ))
                    self._manager.submit((DISCONNECT, self))
                    break

    def write(self, msg):
        msg += "::\r\n"
        self._soc.send(msg.encode("ascii"))

    def shutdown(self):
        self._running = False
        try:
            self._soc.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._soc.close()
        self.join()

    def getID(self):
        return self.ID


class NetworkManager(Thread):
    def __init__(self, observer, server):
        Thread.__init__(self)
        self._serverSocket = socket()
        try:
            self._serverSocket.connect(server)
        except OSError as e:
            print(e)
            sys.exit(-1)
        self._observer = observer
        self._queue = Queue()
        self._backward = {}
        self._members = {}
        self._forward = None
        self._peerListener = None
        self._aliveKeeper = None
        self._connectionKeeper = None
        self._MSID = None
        self._me = None
        self._running = True

    def _request(self, message):
        send = message + "::\r\n"
        self._serverSocket.send(send.encode("ascii"))
        print("[Server Sent]: " + message)
        received = ""
        while True:
            m = self._serverSocket.recv(1024)
            received += m.decode("ascii")
            if len(received) > 4 and received[-4:] == "::\r\n":
                print("[Server Received]: " + received[:-4])
                return received[:-4]

    def _parseJoin(self, received):
        result = received.split(':')
        MSID = result[0]
        if MSID != self._MSID:
            temp = {}
            i = 1
            while i != len(result):
                ID = sdbm_hash("".join(result[i, i + 3]))
                if ID in self._members:
                    m = self._members[ID]
                else:
                    m = Member(result[i], result[i + 1], int(result[i + 2]))
                temp[ID] = m
                i += 3
            added = [temp[m].getName()
                     for m in temp if m not in self._members]
            removed = [self._members[m].getName()
                       for m in self._members if m not in temp]
            self._members = temp
            if added:
                self._observer.update((ADD, added))
            if removed:
                self._observer.update((REMOVE, removed))
            self._MSID = MSID

    def _connect(self):
        pass

    def _handshake(self):
        pass

    def _accept(self, soc):
        pass

    def _addForward(self, member, msgID, soc):
        pass

    def _addBackward(self, member, msgID, soc):
        pass

    def _receive(self, message, handler):
        pass

    def _processMessage(self, message):
        pass

    def _broadcast(self, notSend, message):
        pass

    def _disconnect(self, handler):
        pass

    def _send(self, message):
        pass

    def run(self):
        while self._running:
            item = self._queue.get()
            if not self._running:
                self._queue.task_done()
                while not self._queue.empty():
                    _ = self._queue.get()
                    self._queue.task_done()
            else:
                if item[0] == ACCEPT:
                    self._accept(item[1])
                elif item[0] == RECEIVE:
                    self._receive(item[1], item[2])
                elif item[0] == CONNECT:
                    self._connect()
                elif item[0] == DISCONNECT:
                    self._disconnect(item[1])
                elif item[0] == KEEP_ALIVE:
                    self._keepAlive()
        # TODO

    def doList(self):
        received = self._request("L")
        if received[0] == 'F':
            raise RemoteException(received[2:])
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        return result

    def doJoin(self, name, room, port):
        pass

    def doSend(self, message):
        pass

    def shutdown(self):
        pass
