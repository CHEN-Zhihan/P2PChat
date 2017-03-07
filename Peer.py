from threading import Thread, Condition
import socket


class ConnectionKeeper(Thread):
    """
    Keep connected
    """
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True
        self._condition = Condition()
        self._sleep = Condition()

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
                    self._manager.submit((RECONNECT, ))

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


class PeerListener(Thread):
    """
    Listen connection requests from peers
    """
    def __init__(self, peerManager, localhost):
        Thread.__init__(self)
        self._peerManager = peerManager
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
    def __init__(self, peerManager, localhost, m):
        Thread.__init__(self)
        self._peerManager = peerManager
        self._soc = soc
        self._member = m
        self._running = True

    def run(self):
        while self._running:
            msg = self._soc.recv(1024).decode("ascii")
            if self._running:
                if len(msg) != 0:
                    print("[Peer Received] {} *{}* ".format(
                        self._soc.getpeername(), msg
                    ))
                    self._peerManager.submit((RECEIVE_MESSAGE, msg, self))
                else:
                    print("[Peer Received] receive disconnect request from",
                          self._member.getName())
                    self._peerManager.submit((DISCONNECT, self))
                    break

    def write(self, msg):
        self._soc.send(msg)

    def shutdown(self):
        self._running = False
        try:
            self._soc.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._soc.close()
        self.join()

    def getID(self):
        return self._member.getID()


class PeerManager(Thread):
    """
    Manage peers
    """
    def __init__(self, chat, serverManager):
        Thread.__init__(self)
        self._chat = chat
        self._serverManager = serverManager
        self._connectionKeeper = None
        self._peerListener = None
        self._peerTasks = Queue()
        self._forward = None
        self._backwards = {}
        self._msgID = 0
        self._ID = None
        self._name = None
        self._room = None
        self._ip = None
        self._port = None
        self._forwardLock = Lock()
        self._backwardsLock = Lock()

    def _connect(self):
        if self._forward is None:
            self._serverManager.keepAlive()
            with self._serverManager.getMemberLock():
                members = self._serverManager.getMembers()
                length = len(members)
                print("[Peer Manager] {} members in total, checking...".
                      format(length))
                if length != 1:
                    IDs = sorted(members.keys())
                    i = (IDs.index(self._ID) + 1) % length
                    while IDs[i] != self._ID:
                        if IDs[i] not in self._backwards:
                            try:
                                forward = socket.socket(socket.AF_INET,
                                                        socket.SOCK_STREAM)
                                forward.connect(members[IDs[i]].getHost())
                            except Exception as e:
                                print("[Peer Manager] Error connecting to ",
                                      members[IDs[i]], e)
                                del forward
                            else:
                                result = self._handshake(forward)
                                if result >= 0:
                                    self._addForward(members[IDs[i]],
                                                     result, forward)
                                    break
                                else:
                                    del forward
                        else:
                            print("[Peer Manager] {} is in backwards, aborted".
                                  format(members[IDs[i]]))
                        i = (i + 1) % length
                else:
                    print("[Peer Manager] No others in the room")
            if self._forward is None:
                print("[Peer Manager] Connection Failed rescheduled later")
                self._connectionKeeper.schedule()

    def _handshake(self, to):
        result = False
        message = "P:{}:{}:{}:{}:{}::\r\n".format(self._room, self._name,
                                                  self._ip, self._port,
                                                  self._msgID)
        to.settimeout(10)
        to.send(message.encode("ascii"))
        try:
            received = to.recv(1024).decode("ascii")
        except socket.timeout:
            print("[ERROR] Handshake timeout, delete ", to.getpeername())
            return -1
        else:
            if received[:2] != "S:" or received[-4:] != "::\r\n":
                print("[ERROR] Incorrect handshake confirmation", received)
                return -1
        to.settimeout(None)
        return int(received[2:-4])

    def _accept(self, new):
        new.settimeout(10)
        try:
            received = new.recv(1024).decode("ascii")
        except socket.timeout:
            print("[ERROR] Not receiving handshaking from {}, closed".format(
                  newSocket.getpeername()))
            new.close()
            del new
        else:
            new.settimeout(None)
            if len(received) > 4 and received[:2] == "P:" and \
               received[-4:] == "::\r\n":
                result = received[2:-4].split(':')
                if len(result) == 5 and result[0] == self._room and \
                   result[2] == new.getpeername()[0]:
                    ID = sdbm_hash("{}{}{}".format(result[1],
                                                   result[2], result[3]))
                    member = self._serverManager.getMember(ID)
                    if member is not None:
                        self._addBackward(member, int(result[4]), new)
                    else:
                        print("[Peer Manager] No such user {}, closed".
                              format(result[1]))
                        new.close()
                else:
                    print("[ERROR] Received {} from {}, closed".format(
                           received, new.getpeername()
                         ))
                    new.close()
            else:
                print("[ERROR] Received {} from {}, closed".format(
                        received, new.getpeername()
                        ))
                new.close()

    def _addForward(self, member, msgID, soc):
        with self._forwardLock:
            m = member
            m.setMsgID(msgID)
            self._forward = PeerHandler(self, soc, m)
            self._forward.start()
        print("[Peer Manager] Add forward Link to ", m.getName())

    def _addBackward(self, member, msgID, soc):
        m = member
        m.setMsgID(msgID)
        soc.send("S:{}::\r\n".format(self._msgID).encode("ascii"))
        print("[Peer Manager] send hand shake confirm to", member)
        with self._backwardsLock:
            temp = PeerHandler(self, soc, m)
            self._backwards[m.getID()] = temp
            temp.start()
        print("[Peer Manager] Add Backward Link to ", m.getName())

    def _receive(self, message, handler):
        if message[:2] != "T:" or message[-4:] != "::\r\n":
            print("[ERROR] receive illegal message: {}, drop",
                  message)
        else:
            self._process(message[2:-4])

    def _process(self, message):
        roomLength = len(self._room)
        if message[:len(self._room)] != self._room:
            print("[ERROR] Wrong room number received,drop: {}".
                  format(message))
            return
        try:
            message = message[roomLength + 1:]
            result = []
            for k in range(5):
                i = message.index(':')
                result.append(message[:i])
                message = message[i + 1:]
                if k >= 3 or k == 0:
                    result[k] = int(result[k])
            print(result)
        except Exception as e:
            print(e)

    def _broadcast(self, prohibited, msg):
        if self._forward and self._forward not in prohibited:
            self._forward.write(msg)
        for backward in self._backwards.keys():
            if backward not in prohibited:
                self._backwards[backward].write(msg)

    def submit(self, task):
        self._peerTasks.put(task)

    def shutdown(self):
        self.submit(None)
        print("waiting Peer Manager to be Joined")
        if self.is_alive():
            self.join()

    def _disconnect(self, handler):
        handler.shutdown()
        with self._forwardLock:
            result = self._forward == handler
        if result:
            with self._forwardLock:
                self._forward = None
            print("[Peer Manager] Forward Link Disconnected")
            self._connect()
        else:
            self._backwards.pop(handler.getID())
            print("[Peer Manager] Backward Link {} Disconnected".
                  format(handler))

    def run(self):
        self._setInfo()
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.bind((self._ip, self._port))
        self._peerListener = PeerListener(self, soc)
        self._peerListener.start()
        self._connectionKeeper = ConnectionKeeper(self)
        self._connectionKeeper.start()
        self._connect()
        while True:
            print("[Peer Manager] Waiting for task...")
            task = self._peerTasks.get()
            print("[Peer Manager] Task Received, ", task)
            if not task:
                self._peerTasks.task_done()
                break
            if task[0] == NEW_CONNECTION:
                self._accept(task[1])
            elif task[0] == RECEIVE_MESSAGE:
                self._receive(task[1], task[2])
            elif task[0] == RECONNECT:
                self._connect()
            elif task[0] == DISCONNECT:
                self._disconnect(task[1])
            self._peerTasks.task_done()
        self._peerListener.shutdown()
        self._connectionKeeper.shutdown()
        if self._forward:
            self._forward.shutdown()
        for handler in self._backwards.values():
            handler.shutdown()

    def _setInfo(self):
        name, room, ip, port, ID = self._serverManager.getInfo()
        self._name = name
        self._room = room
        self._ip = ip
        self._port = port
        self._ID = ID

    def send(self, message):
        msgID = self._msgID
        self._msgID += 1
        length = len(message)
        m = "T:{}:{}:{}:{}:{}:{}::\r\n".format(self._room,
                                               self._ID, self._name, msgID,
                                               length, message)
        self._broadcast([self._ID], message.encode("ascii"))