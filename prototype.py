from tkinter import *
import sys
import socket
from threading import Thread, Condition, Lock
from queue import Queue

START_STATE = 0
NAMED_STATE = 1
JOINED_STATE = 2
CONNECTED_STATE = 3
NEW_CONNECTION = 0
RECEIVE_MESSAGE = 1
RECONNECT = 2
ADD = 1
REMOVE = 2


class UnnamedException(Exception):
    pass


class UnjoinedException(Exception):
    pass


class JoinedException(Exception):
    pass


class RemoteException(Exception):
    """
    Exception on the room server
    """
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


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
        Thread.__init__(self)
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
            try:
                new, address = self._soc.accept()
            except OSError:
                if not self._running:
                    break
            else:
                if self._running:
                    self._peerManager.submit((NEW_CONNECTION, new))

    def shutdown(self):
        self._running = False
        self._soc.shutdown(socket.SHUT_RD)
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
        self._backwards = []
        self._msgID = 0

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
                                    self._addForward(members[i],
                                                     result, forward)
                                    break
                                else:
                                    del forward
                        i = (i + 1) % length
                    if self._forward is None:
                        self._connectionKeeper.schedule()

    def _handshake(self, to):
        result = False
        message
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
                print("Incorrect handshake confirmation, delete",
                      to.getpeername())
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
                if len(result) == 5 and result[0] == self._room and \
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
            print(result)
        except Exception as e:
            print(e)

    def _broadcast(self, msg):
        pass

    def submit(self, task):
        self._peerTasks.put(task)

    def shutdown(self):
        self._running = False
        self._peerTasks.join()
        if self._peerListener:
            self._peerListener.shutdown()
        if self._connectionKeeper:
            self._connectionKeeper.shutdown()
        if self._forward:
            self._forward.shutdown()
        for handler in self._backwards:
            handler.shutdown()
        self.submit(None)
        self.join()

    def run(self):
        self._setInfo()
        self._connectionKeeper = ConnectionKeeper(self)
        self._connectionKeeper.start()
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.bind((self._ip, self._port))
        self._peerListener = PeerListener(self, soc)
        self._peerListener.start()
        while True:
            task = self._peerTasks.get()
            if not task:
                break
            if task[0] == NEW_CONNECTION:
                self._accept(task[1])
            elif task[0] == RECEIVE_MESSAGE:
                self._receive(task[1], task[2])
            elif task[0] == RECONNECT:
                self._connect()

    def _setInfo(self):
        name, room, ip, port = self._serverManager.getInfo()
        self._name = name
        self._room = room
        self._ip = ip
        self._port = port


class ServerManager(object):
    """
    Manage servers
    """
    def __init__(self, chat, soc):
        self._chat = chat
        self._serverSocket = soc
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
                added = [temp[m].getName()
                         for m in temp if m not in self._members]
                removed = [self._members[m].getName()
                           for m in self._members if m not in temp]
                self._members = temp
            if added:
                self._chat.update((ADD, added))
            if removed:
                self._chat.update((REMOVE, removed))

    def doList(self):
        received = self._request("L")
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
        self._room = room
        self._setInfo()
        self._aliveKeeper.start()

    def getMembers(self):
        return self._members

    def getMemberLock(self):
        return self._memberLock

    def shutdown(self):
        self._serverSocket.close()
        if self._aliveKeeper:
            self._aliveKeeper.shutdown()

    def _setInfo(self):
        name, ip, port = self._chat.getInfo()
        self._name = name
        self._ip = ip
        self._port = port

    def getInfo(self):
        return (self._name, self._room, self._ip, self._port)


class P2PChat(object):
    def __init__(self, server, port, observer):
        self._state = START_STATE
        self._name = None
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.connect(server)
        self._server = ServerManager(self, soc)
        self._peer = PeerManager(self, self._server)
        self._observer = observer
        self._port = port
        self._ip = soc.getsockname()[0]

    def doJoin(self, room):
        """
        Check the state, if it is named and unjoined,
        give NetworkManager corresponding information and
        call do_Join(). Update state afterwards.
        """
        if self._state >= JOINED_STATE:
            raise JoinedException()
        if self._state == START_STATE:
            raise UnnamedException()
        self._server.doJoin(room)
        self._peer.start()
        self._state = JOINED_STATE

    def doList(self):
        return self._server.doList()

    def doQuit(self):
        self._server.shutdown()
        self._peer.shutdown()

    def doSend(self):
        pass

    def doUser(self, username):
        if self._state > NAMED_STATE:
            raise JoinedException()
        self._name = username
        self._state = NAMED_STATE

    def update(self, l):
        """
        Inform GUI there's an update.
        """
        self._observer.update(l)

    def getInfo(self):
        return (self._name, self._ip, self._port)


class P2PChatUI(object):
    def __init__(self, argv):
        #
        # Set up of Basic UI
        #
        self._chat = P2PChat((argv[1], int(argv[2])), int(argv[3]), self)
        self._first = True
        win = Tk()
        win.title("MyP2PChat")

        # Top Frame for Message display
        topframe = Frame(win, relief=RAISED, borderwidth=1)
        topframe.pack(fill=BOTH, expand=True)
        topscroll = Scrollbar(topframe)
        self.MsgWin = Text(topframe, height='15', padx=5, pady=5, fg="red",
                           exportselection=0, insertofftime=0)
        self.MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
        topscroll.pack(side=RIGHT, fill=Y, expand=True)
        self.MsgWin.config(yscrollcommand=topscroll.set)
        topscroll.config(command=self.MsgWin.yview)

        # Top Middle Frame for buttons
        topmidframe = Frame(win, relief=RAISED, borderwidth=1)
        topmidframe.pack(fill=X, expand=True)
        Butt01 = Button(topmidframe, width='8',
                        relief=RAISED, text="User", command=self.do_User)
        Butt01.pack(side=LEFT, padx=8, pady=8)
        Butt02 = Button(topmidframe, width='8',
                        relief=RAISED, text="List", command=self.do_List)
        Butt02.pack(side=LEFT, padx=8, pady=8)
        Butt03 = Button(topmidframe, width='8',
                        relief=RAISED, text="Join", command=self.do_Join)
        Butt03.pack(side=LEFT, padx=8, pady=8)
        Butt04 = Button(topmidframe, width='8',
                        relief=RAISED, text="Send", command=self.do_Send)
        Butt04.pack(side=LEFT, padx=8, pady=8)
        Butt05 = Button(topmidframe, width='8',
                        relief=RAISED, text="Quit", command=self.do_Quit)
        Butt05.pack(side=LEFT, padx=8, pady=8)

        # Lower Middle Frame for User input
        lowmidframe = Frame(win, relief=RAISED, borderwidth=1)
        lowmidframe.pack(fill=X, expand=True)
        self.userentry = Entry(lowmidframe, fg="blue")
        self.userentry.pack(fill=X, padx=4, pady=4, expand=True)

        # Bottom Frame for displaying action info
        bottframe = Frame(win, relief=RAISED, borderwidth=1)
        bottframe.pack(fill=BOTH, expand=True)
        bottscroll = Scrollbar(bottframe)
        self.CmdWin = Text(bottframe, height='15', padx=5, pady=5,
                           exportselection=0, insertofftime=0)
        self.CmdWin.pack(side=LEFT, fill=BOTH, expand=True)
        bottscroll.pack(side=RIGHT, fill=Y, expand=True)
        self.CmdWin.config(yscrollcommand=bottscroll.set)
        bottscroll.config(command=self.CmdWin.yview)
        win.mainloop()
    #
    # Functions to handle user input
    #

    def do_Quit(self):
        self._chat.doQuit()
        sys.exit(0)

    def do_Send(self):
        self.CmdWin.insert(1.0, "\nPress Send")

    def do_Join(self):
        """
        Validate the input, and call P2PChat's do_Join.
        Handle exception and print errors.
        """
        room = self.userentry.get()
        if self._valid(room):
            try:
                self._chat.doJoin(room)
            except JoinedException:
                self._cmd("[ERROR] Cannot join another room")
            except UnnamedException:
                self._cmd("[ERROR] Cannot join without name")
        else:
            self._cmd("[ERROR] Invalid roomname")
        self.userentry.delete(0, END)

    def do_List(self):
        """
        Call P2PChat's do_List.
        Handle exception and print results.
        """
        try:
            result = self._chat.doList()
        except RemoteException as e:
            self._cmd("[ERROR] " + e)
        else:
            if not result:
                self._cmd("[LIST] No chatroom available")
            else:
                for i in result:
                    self._cmd(i)
                self._cmd("[LIST] list all chatroom(s)")

    def do_User(self):
        """
        Validate the input, and call P2PChat's do_User.
        Handle exception and print errors.
        """
        username = self.userentry.get()
        if self._valid(username):
            try:
                self._chat.doUser(username)
            except JoinedException:
                self._cmd("[ERROR] Cannot Rename after Join")
            else:
                self._cmd("[USER] username: " + username)
        else:
            self._cmd("[ERROR] Invalid username")
        self.userentry.delete(0, END)

    def _cmd(self, message):
        """
        Print to command window.
        """
        self.CmdWin.insert(1.0, "\n" + message)

    def _valid(self, name):
        """
        Validate information
        """
        return len(name) != 0 and all(map((lambda x: x != ':'), name))

    def update(self, message):
        """
        Print updated information.
        """
        if message[0] == ADD:
            for i in message[1]:
                self._cmd(i)
            if self._first:
                self._cmd("[ROOM] List all members:")
                self._first = False
            else:
                self._cmd("[ROOM] user(s) joined:")
        else:
            for i in message[1]:
                self._cmd(i)
            self._cmd("[ROOM] user(s) left:")


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)
    P2PChatUI(sys.argv)


if __name__ == "__main__":
    main()
