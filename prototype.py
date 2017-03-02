from tkinter import *
import sys
import socket
from threading import Thread, Condition, Event
from queue import Queue

NEW_CONNECTION = 0
RECEIVE_MESSAGE = 1
RECONNECT = 2

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
            self._manager.keepAlive()
            self._condition.acquire()
            self._condition.wait(20)
            self._condition.release()

    def shutdown(self):
        self._running = False
        self.notify()
        self.join()

    def notify(self):
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()


class ConnectionKeeper(Thread):
    """
    Keep connected
    """
    def __init__(self, manager):
        self._manager = manager
        self._running = True
        self._condition = Condition()

    def run(self):
        while self._running:
            self._condition.acquire()
            self._condition.wait()
            self._condition.release()
            if self._running:
                sleep(5)
                self._manager.submit((RECONNECT))

    def schedule(self):
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()

    def shutdown(self):
        self._running = False
        self.schedule()


class PeerListener(Thread):
    """
    Listen connection requests from peers
    """
    def __init__(self, peerManager, soc):
        Thread.__init__(self)
        self._peerManager = peerManager
        self._soc = soc
        self._soc.listen(5)
        self._running = True

    def run(self):
        while self._running:
            new, address = self._soc.accept()
            if self._running:
                self._peerManager.submit((NEW_CONNECTION, new))

    def shutdown(self):
        self._running = False
        self._soc.shutdown(socket.SHUT_RDWR)
        self._soc.close()
        self.join()


class PeerHandler(Thread):
    """
    Handle message sent from peers
    """
    def __init__(self, peerManager, soc, m):
        Thread.__init__(self)
        self._peerManager = peerManager
        self._soc = soc
        self._member = m
        self._running = True

    def run(self):
        while self._running:
            msg = self._soc.recv(1024).decode("ascii")
            if self._running:
                self._peerManager.submit((RECEIVE_MESSAGE, msg, self))

    def write(self, msg):
        self._soc.send(msg.encode("ascii"))

    def shutdown(self):
        self._running = False
        self._soc.shutdown(socket.SHUT_RDWR)
        self._soc.close()
        self.join()


class BaseManager(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._room = None
        self._name = None
        self._ip = None
        self._port = None

    def setInfo(self, room, name, ip, port):
        self._room = room
        self._name = name
        self._ip = ip
        self._port = port


class PeerManager(Thread):
    """
    Manage peers
    """
    def __init__(self, m, serverManager):
        self._chat = m
        self._serverManager = serverManager
        self._connectionKeeper = None
        self._peerTasks = Queue()
        self._forward = None
        self._backwards = []

    def _connect(self):
        if self._forward is None:
            with self._serverManager.getMemberLock():
                members = self._serverManager.getMembers()
                length = len(members)
                if length != 1:
                    IDs = sorted(members.keys())
                    myID = self._chat.getID()
                    i = (IDs.index(myID) + 1) % length
                    while IDs[i] != myID:
                        if IDs[i] not in self._backwards and length != 2:
                            try:
                                forward = socket.socket(socket.AF_INET,
                                                        socket.SOCK_STREAM)
                                forward.connect(members[i].getHost())
                            except Exception as e:
                                print("Error connecting to ", members[i], e)
                                del forward
                            else:
                                result = self._handshake(forward)
                                if result >= 0:
                                    self._addForward(members[i], result, forward)
                                    break
                                else:
                                    del forward
                        i = (i + 1) % length
                    if self._forward is None:
                        self._connectionKeeper.schedule()

    def _handshake(self, to):
        result = False
        message = "P:{}:{}:{}:{}:{}".format(self._room, self._name,
                                            self._ip, self._port, self._msgID)
        to.settimeout(10)
        to.send(message.encode("ascii"))
        try:
            received = to.recv(1024).decode("ascii")
        except timeout:
            print("Handshake timeout, delete ", to.getpeername())
            return -1
        else:
            if received[:2] != "S:" or received[:-4] != "::\r\n":
                print("Incorrect handshake confirmation, delete", to.getpeername())
                return -1
        to.settimeout(None)
        return int(received[2:-4])

    def _accept(self, new):
        new.settimeout(10)
        try:
            received = new.recv(1024).decode("ascii")
        except timeout:
            print("Not receiving handshaking from {}, closed".format(
                  newSocket.getpeername()))
            new.close()
            del new
        else:
            new.settimeout(None)
            if received[:2] == "P:" and received[-4:] == "::\r\n":
                result = message[2:-4].split(':')
                if len(result) == 5 and result[0] == self._room and
                result[2] == new.getpeername()[0]:
                    ID = sdbm_hash("{}{}{}".format(result[1],
                                                   result[2], result[3]))
                    member = self._serveManager.getMember(ID)
                    if member is not None:
                        self._addBackward(self, member, int(result[4]), new)
                else:
                    print("Received {} from {}, closed".format(
                           message, new.getpeername()
                         ))
                    new.close()
            else:
                print("Received {} from {}, closed".format(
                        message, new.getpeername()
                        ))
                new.close()

    def _addForward(self, member, msgID, soc):
        m = member
        m.setMsgID(msgID)
        self._forward = PeerHandler(self, soc, m)
        self._forward.start()

    def _addBackward(self, member, msgID, soc):
        m = member
        m.setMsgID(msgID)
        temp = PeerHandler(self, soc, m)
        self._backwards.append(temp)
        temp.start()

    def _receive(self, message, handler):
        if len(message) == 0:
            handler.shutdown()
            if self._forward == handler:
                self._forward = None
                self._connect()
            else:
                self._backwards.remove(handler)
        else:
            if message[:2] != "T:" or message[-4:] != "::\r\n":
                print("receive illegal message: {}, shut down", message)
                handler.shutdown()
                self._process(message[2:-4])

    def _process(self, message):
        roomLength = len(self._room)
        if message[:len(self._room)] != self._room:
            print("Wrong room number received,drop: {}".format(message))
            return
        try:
            message = message[roomLength + 1:]
            result = []
            for k in range(5):
                i = message.index(':')
                result.append(message[:i])
                message = message[i + 1:]
                if k >= 3:
                    result[k] = int(result[k])
            pass

    def _broadcast(self, msg):
        pass

    def submit(self, task):
        self._peerTasks.put(task)

    def doQuit(self):
        self._running = False
        self._peerTasks.join()
        if self._forward:
            self._forward.shutdown()
        for handler in self._backwards:
            handler.shutdown()
        self.join()

    def run(self):
        while self._running:
            task = self._peerTasks.get()
            if task[0] == NEW_CONNECTION:
                self._accept(task[1])
            elif task[0] == RECEIVE_MESSAGE:
                self._receive(task[1], task[2])
            elif task[0] == RECONNECT:
                self._connect()


class ServerManager(object):
    """
    Manage servers
    """
    def __init__(self, m, server):
        self._chat = m
        self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSocket.connect(server)
        self._aliveKeeper = AliveKeeper(self)
        self._requestLock = Lock()
        self._memberLock = Lock()
        self._members = {}
        self._MSID = ""

    def _request(self, message):
        with self._requestLock:
            send = message + "::\r\n"
            self._serverSocket.send(send.encode("ascii"))
            print("[Sent to server]: " + message)
            received = ""
            while True:
                m = self._serverSocket.recv(1024)
                received += m.decode("ascii")
                if len(received) > 4 and received[-4:] == "::\r\n":
                    print("[Received from server]: " + received[:-4])
                    return received[:-4]

    def _parseJoin(self, received):
        result = received.split(':')
        MSID = result[0]
        if MSID != self._MSID:
            temp = {}
            i = 1
            while i != len(result):
                m = Member(result[i], result[i + 1], int(result[i + 2]))
                temp[m.getID()] = m
                i += 3
            with self._memberLock:
                added = [temp[m].getName() for m in temp if m not in self._members]
                removed = [self._members[m].getName() for m in self._members if m not in temp]
                self._members = temp
            if added:
                self._chat.update((ADD, added))
            if removed:
                self._chat.update((REMOVE, removed))

    def doList(self):
        result = self._request("L")
        if received[0] == 'F':
            raise RemoteException(received[2:])
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        return result

    def keepAlive(self):
        request = "J:{}:{}:{}:{}".format(self._room, self._name,
                                         self._ip, self._port)
        received = self._request(request)
        if received[0] == 'F':
            raise RemoteException(received[1:])
        self._parseJoin(received[2:])

    def getMember(self, ID):
        exist = False
        with self._memberLock:
            if ID in self._members:
                exist = True
        if not exist:
            self.keepAlive()
        with self._memberLock:
            if ID in self._members:
                exist = True
        return self._members[ID] if exist else None

    def doJoin(self, room):
        self._aliveKeeper.start()

    def getMembers(self):
        return self._members

    def getMemberLock(self):
        return self._memberLock


class P2PChat(object):
    def __init__(self, server, port):
        