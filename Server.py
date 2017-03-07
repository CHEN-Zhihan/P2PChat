from threading import Condition, Thread
from queue import Queue


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
            self._manager.keepAlive()

    def shutdown(self):
        self._running = False
        self.notify()
        self.join()


class ServerManager(Thread):
    def __init__(self, chat, server):
        Thread.__init__(self)
        self._chat = chat
        self._members = {}
        self._serverSocket = socket.socket()
        self._queue = Queue()
        self._running = True
        self._MSID = None
        self._joinMessage = None
        self._aliveKeeper = None
        try:
            self._serverSocket.connect(server)
        except OSError as e:
            print(e)
            sys.exit(-1)

    def _request(self, message):
        message += "::\r\n"
        self._serverSocket.send(message.encode("ascii"))
        print("[Server Sent]: " + message)
        received = ""
        while True:
            try:
                m = self._serverSocket.recv(1024)
            except OSError as e:
                print(e)
            else:
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
                newID = sdbm_hash("".join(result[i:i + 3]))
                if newID in self._members:
                    m = self._members[newID]
                else:
                    m = Member(result[i], result[i + 1], int(result[i + 2]))
                temp[newID] = m
                i += 3
            added = [temp[m].getName()
                     for m in temp if m not in self._members]
            removed = [self._members[m].getName()
                       for m in self._members if m not in temp]
            self._members = temp
            if added:
                self._chat.update((ADD, added))
            if removed:
                self._chat.update((REMOVE, removed))

    def _keepAlive(self):
        received = self._request(self._joinMessage)
        if received[0] == 'F':
            raise RemoteException(received[1:])
        self._parseJoin(received[2:])

    def _getMember(self, item):
        

    def run(self):
        while self._running:
            item = self._queue.get()
            if not self._running:
                self._queue.task_done()
                while not self._queue.empty():
                    _ = self._queue.get()
                    self._queue.task_done()
            else:
                if item[0] == DO_JOIN:
                    self._keepAlive()
                elif item[0] == GET_MEMBERS:
                    item[1](self._members)
                elif item[0] == GET_MEMBER:
                    self._getMember(item[1:])

    def doList(self):
        received = self._request("L")
        if received[0] == 'F':
            raise RemoteException(received[2:])
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        return result

    def doJoin(self, name, room, port):
        ip = self._serverSocket.getsockname()[0]
        self._joinMessage = "J:{}:{}:{}:{}".format(
            room, name, ip, port
        )
        self._aliveKeeper = AliveKeeper(self)
        self._aliveKeeper.start()

    def shutdown(self):
        self._running = False
        self.submit(None)
        if self._aliveKeeper:
            self._aliveKeeper.shutdown()
        self._serverSocket.close()
        self.join()