"""
Student Name: CHEN, Zhihan
UID: 3035142261
Development Platform: Ubuntu 16.04 LTS x64
Python Version: Python 3.5.2
Version: stage 2
"""

from tkinter import *
import sys
import socket
from threading import Thread, Condition, Lock, Event
from queue import Queue
import sys
import chat


USER_JOINED = ${USER_JOINED}
chat.doJoin("hello world")
chat.doSend("this is send")
print(chat.doList())
print(chat.doUser("this is user"))
chat.doQuit("this is quit")
"""
Global variable indicating states
"""
START_STATE = 0
NAMED_STATE = 1
JOINED_STATE = 2

"""
Global variables indicating actions to be taken
"""
KEEP_ALIVE = "KEEP_ALIVE"
CONNECT = "CONNECT"
ACCEPT = "ACCEPT"
RECEIVE = "RECEIVE"
DISCONNECT = "DISCONNECT"
SEND = "SEND"
DO_LIST = "DO_LIST"
"""
Variables indicate the observer what to do
"""
OBSERVE_ADD = 1
OBSERVE_REMOVE = 2
OBSERVE_FORWARD = 3
OBSERVE_BACKWARD = 4
OBSERVE_ERROR = 5
OBSERVE_MESSAGE = 6
OBSERVE_LIST = 7

"""
These are classes for handling illegal transitions
"""


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
    """
    This is an abstraction of members
    """

    def __init__(self, name, ip, port, msgID=0):
        self._name = name
        self._ip = ip
        self._port = port
        self._msgID = msgID
        self._ID = sdbm_hash("{}{}{}".format(name, ip, port))

    def getID(self):
        return self._ID

    def getHost(self):
        return (self._ip, self._port)

    def setMsgID(self, msgID):
        self._msgID = msgID

    def getMsgID(self):
        return self._msgID

    def hasSent(self, msgID):
        return self._msgID >= msgID

    def sendOne(self):
        self._msgID += 1

    def getName(self):
        return self._name

    def __str__(self):
        return "{}@{}".format(self._name, self.getHost())


class AliveKeeper(Thread):
    """
    A seprate thread for KEEPALIVE strategy.
    """

    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True
        self._condition = Condition()
        self._postpone = False

    def run(self):
        while self._running:
            self._condition.acquire()
            self._condition.wait(20)
            self._condition.release()
            if self._running:
                if self._postpone:
                    self._postpone = False
                    continue
                self._manager.submit((KEEP_ALIVE, ))

    def shutdown(self):
        self._running = False
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()
        if self.is_alive():
            self.join()

    def postpone(self):
        """
        To be called when another request (e.g., connect) invokes keepAlive(),
        So that this thread can postpone next keepAlive request
        """
        self._postpone = True
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()


class ConnectionKeeper(Thread):
    """
    A separate thread monitoring connection status.
    It will normally be blocked.
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
                self._sleep.wait(timeout=5)
                self._sleep.release()
                if self._running:
                    self._manager.submit((CONNECT, ))

    def schedule(self):
        """
        When the connect() method cannot establish connection immediately,
        Call schedule to execute connect() 5 seconds later.
        """
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()

    def shutdown(self):
        self._running = False
        self.schedule()
        self._sleep.acquire()
        self._sleep.notify()
        self._sleep.release()
        if self.is_alive():
            self.join()


class PeerListener(Thread):
    """
    Listen connection requests from peers
    """

    def __init__(self, manager, soc):
        Thread.__init__(self)
        self._manager = manager
        self._soc = soc
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
                    self._manager.submit((ACCEPT, new))

    def shutdown(self):
        self._running = False
        self._soc.shutdown(socket.SHUT_RDWR)
        self._soc.close()
        if self.is_alive():
            self.join()


class PeerHandler(Thread):
    """
    Handle message sent from each peer.
    """

    def __init__(self, manager, ID, soc):
        Thread.__init__(self)
        self._manager = manager
        self._ID = ID
        self._running = True
        self._soc = soc

    def run(self):
        while self._running:
            try:
                msg = self._soc.recv(1024).decode("ascii")
            except OSError as e:
                print("[ERROR] error in peer receiving", e)
                self._manager.submit((DISCONNECT, self))
                break
            else:
                if self._running:
                    if len(msg) != 0:
                        print("[Peer Received] {} *{}* ".format(
                            self._soc.getpeername(), msg
                        ))
                        self._manager.submit((RECEIVE, msg, self._ID))
                    else:
                        print("[Peer Received] receive disconnect request")
                        self._manager.submit((DISCONNECT, self))
                        break

    def write(self, msg):
        """
        Send message to the peer corresponding to this handler
        """
        try:
            self._soc.send(msg)
        except OSError as e:
            print("[ERROR] error in peer writing", e)
            self._manager.submit((DISCONNECT, self))

    def shutdown(self):
        self._running = False
        try:
            self._soc.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._soc.close()
        if self.is_alive():
            self.join()

    def getID(self):
        return self._ID


class ServerManager(object):
    """
    This is a class that handles traffic between this client and the room server.
    """

    def __init__(self, manager, server, observer):
        self._manager = manager
        self._serverSocket = socket.socket()
        try:
            self._serverSocket.connect(server)
        except OSError as e:
            print(e)
            sys.exit(-1)
        self._members = {}
        self._MSID = None
        self._aliveKeeper = AliveKeeper(self._manager)
        self._observer = observer
        self._joinMessage = None

    def _request(self, message):
        """
        Send request to the room server and wait for its response.
        """
        send = message + "::\r\n"
        try:
            self._serverSocket.send(send.encode("ascii"))
        except OSError as e:
            print("[ERROR] cannot send to server", e)
        print("[Server Sent]: " + message)
        received = ""
        while True:
            try:
                m = self._serverSocket.recv(1024)
            except OSError as e:
                if not self._running:
                    pass
                else:
                    print("[ERROR] receiving from server", e)
                    sys.exit(-1)
            received += m.decode("ascii")
            if len(received) > 4 and received[-4:] == "::\r\n":
                print("[Server Received]: " + received[:-4])
                return received[:-4]

    def keepAlive(self, postpone=False):
        """
        Method to keep this client alive. If it is necessary to postpone next
        keepAlive call to aliveKeeper, set postpone to be True.
        It sends a JOIN request to room server, parses the result and update the
        membership list if necessary
        """
        if postpone:
            self._aliveKeeper.postpone()
        received = self._request(self._joinMessage)
        if received[0] == "F":
            self._observer.update((OBSERVE_ERROR, received[2:]))
        else:
            result = received.split(':')[1:]
            MSID = result[0]
            if MSID != self._MSID:
                temp = {}
                i = 1
                while i != len(result):
                    ID = sdbm_hash("".join(result[i: i + 3]))
                    if ID in self._members:
                        m = self._members[ID]
                    else:
                        m = Member(result[i], result[i + 1],
                                   int(result[i + 2]))
                    temp[ID] = m
                    i += 3
                added = [temp[m].getName()
                         for m in temp if m not in self._members]
                removed = [self._members[m].getName()
                           for m in self._members if m not in temp]
                self._members = temp
                if added:
                    self._observer.update((OBSERVE_ADD, added))
                if removed:
                    self._observer.update((OBSERVE_REMOVE, removed))
                self._MSID = MSID

    def getMember(self, ID):
        """
        get Member by ID. This is to be called by NetworkManager
        """
        if ID in self._members:
            return self._members[ID]
        self.keepAlive(True)
        return self._members[ID] if ID in self._members else None

    def getMembers(self):
        """
        get All members, This is to be called by NetworkManager
        """
        return self._members

    def getIP(self):
        """
        get localhost IP
        """
        return self._serverSocket.getsockname()[0]

    def doJoin(self, name, room, port):
        """
        Setup join message and start AliveKeeper
        """
        ip = self._serverSocket.getsockname()[0]
        self._joinMessage = "J:{}:{}:{}:{}".format(
            room, name, ip, port
        )

        self._aliveKeeper.start()

    def doList(self):
        """
        Send LIST request to room server, and inform the observer about the result
        """
        received = self._request("L")
        if received[0] == 'F':
            self._observer.update((OBSERVE_ERROR, received[2:]))
            return
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        self._observer.update((OBSERVE_LIST, result))

    def shutdown(self, joined=True):
        if joined:
            self._aliveKeeper.shutdown()
        try:
            self._serverSocket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self._serverSocket.close()


class PeerManager(object):
    """
    This is a manager handling events related to peers
    """

    def __init__(self, manager, observer):
        self._manager = manager
        self._observer = observer
        self._backward = {}
        self._forward = None
        self._connectionKeeper = ConnectionKeeper(self._manager)
        self._peerListener = None
        self._me = None
        self._room = None
        self._handshakeMessage = None

    def _handshake(self, soc):
        """
        It sends a handshake message to soc, which is passed by connect().
        If it does not receive correct handshake information intime, it will return
        -1 indicating error. On success, return the msgID of peer.
        """
        result = False
        message = self._handshakeMessage + "{}::\r\n".format(
            self._me.getMsgID()
        )
        soc.settimeout(10)
        try:
            soc.send(message.encode("ascii"))
        except OSError as e:
            print("[ERROR] cannot send handshake", e)
            return -1
        try:
            received = soc.recv(1024).decode("ascii")
        except socket.timeout:
            print("[ERROR] Handshake timeout, delete ", soc.getpeername())
            return -1
        except OSError as e:
            print("[ERROR]Cannot receive handshake", e)
            return -1
        else:
            if received[:2] != "S:" or received[-4:] != "::\r\n":
                print("[ERROR] Incorrect handshake confirmation", received)
                return -1
        soc.settimeout(None)
        return int(received[2:-4])

    def _addForward(self, member, msgID, soc):
        """
        Add a member, his/her msgID and the corresponding socket to
        forward link
        """
        member.setMsgID(msgID)
        self._forward = PeerHandler(self._manager, member.getID(), soc)
        self._forward.start()
        self._observer.update((OBSERVE_FORWARD, member.getName()))

    def _addBackward(self, member, msgID, soc):
        """
        Add a member, his/her msgID and the corresponding socket to
        backward link
        """
        member.setMsgID(msgID)
        soc.send("S:{}::\r\n".format(self._me.getMsgID()).encode("ascii"))
        temp = PeerHandler(self._manager, member.getID(), soc)
        self._backward[member.getID()] = temp
        temp.start()
        self._observer.update((OBSERVE_BACKWARD, member.getName()))

    def _processMessage(self, message):
        """
        Parse the message received from peers. If the message is incorrect,
        drop it.
        """
        roomLength = len(self._room)
        if message[:len(self._room)] != self._room:
            print("[ERROR] Incorrect room, drop: {}".
                  format(message))
            return None
        message = message[roomLength + 1:]
        result = []
        i = 0
        for k in range(4):
            i = message.index(":")
            result.append(message[:i])
            message = message[i + 1:]
            if k == 0 or k >= 2:
                result[k] = int(result[k])
        result.append(message)
        return result

    def _broadcast(self, notSend, message):
        """
        Send message to every connected peers except for those in notSend list.
        """
        if self._forward and self._forward.getID() not in notSend:
            self._forward.write(message)
        for i in self._backward:
            if i not in notSend:
                self._backward[i].write(message)

    def disconnect(self, handler):
        """
        On receiving disconnect request, remove handler from forward or
        backward link
        """
        handler.shutdown()
        if self._forward == handler:
            self._forward = None
            print("[FORWARD] Disconnected")
            self.connect()
        elif handler in self._backward:
            temp = self._backward.pop(handler.getID())
            print("[BACKWARD] A peer Disconnected")

    def connect(self):
        """
        Proceed the connect procedure. On success, add the target to
        forward link. On failure, schedule ConnectionKeeper to connect
        5 seconds later
        """
        if self._forward is None:
            self._manager.keepAlive()
            members = self._manager.getMembers()
            length = len(members)
            if length != 1:
                IDs = sorted(members.keys())
                myID = self._me.getID()
                i = (IDs.index(myID) + 1) % length
                while IDs[i] != myID:
                    if IDs[i] not in self._backward:
                        try:
                            forward = socket.socket()
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

    def receive(self, message, ID):
        """
        Process message received from ID. If the message is valid,
        check duplication and inform observer. Then broadcast it to all connected
        peers
        """
        if message[:2] != "T:" or message[-4:] != "::\r\n":
            print("[ERROR] receive illegal message: {}, drop",
                  message)
            return
        result = self._processMessage(message[2:-4])
        if result and result[0] != self._me.getID():
            member = self._manager.getMember(result[0])
            if member and member.getName() == result[1]:
                if not member.hasSent(result[2]):
                    member.setMsgID(result[2])
                    self._observer.update(
                        (OBSERVE_MESSAGE, result[4], result[1]))
                    self._broadcast([ID, member.getID()],
                                    message.encode("ascii"))
                else:
                    print("[ERROR] receive duplicated message, drop")
            else:
                print("[ERROR] receive from unknown sender, drop")
        else:
            print("[ERROR] receive message from myself, drop")

    def accept(self, soc):
        """
        Accept a connection from soc. It waits for handshake information,
        checks its sender and validity, and send back confirmation
        if necessary. On timeout, it will disconnect soc.
        """
        soc.settimeout(10)
        try:
            received = soc.recv(1024).decode("ascii")
        except socket.timeout:
            print("[ERROR] Not receiving handshaking from {}, closed".format(
                  socSocket.getpeername()))
        else:
            soc.settimeout(None)
            if len(received) > 4 and received[:2] == "P:" and \
               received[-4:] == "::\r\n":
                result = received[2:-4].split(':')
                if len(result) == 5 and result[0] == self._room and \
                   result[2] == soc.getpeername()[0]:
                    ID = sdbm_hash("".join(result[1:4]))
                    member = self._manager.getMember(ID)
                    if member is not None:
                        self._addBackward(member, int(result[4]), soc)
                        return
                    else:
                        print("[Peer Manager] No such user {}, closed".
                              format(result[1]))
                else:
                    print(len(result), result[0], self._room,
                          result[2], soc.getpeername()[0])
                    print("[ERROR] Received {} from {}, closed".format(
                        received, soc.getpeername()
                    ))
            else:
                print(len(received), received[:2], received[-4:])
                print("[ERROR] Received {} from {}, closed".format(
                    received, soc.getpeername()
                ))
        soc.close()

    def doJoin(self, name, room, ip, port, soc):
        """
        Setup handshake message, start ConnectionKeeper and PeerListener.
        """
        self._me = Member(name, ip, port)
        self._peerListener = PeerListener(self._manager, soc)
        self._room = room
        self._handshakeMessage = "P:{}:{}:{}:{}:".format(
            room, name, ip, port
        )
        self._connectionKeeper.start()
        self._peerListener.start()

    def doSend(self, rawMessage):
        """
        Send rawMessage out. Inform observer and broadcast to every connected
        peers.
        """
        self._me.sendOne()
        message = "T:{}:{}:{}:{}:{}:{}::\r\n".format(
            self._room, self._me.getID(), self._me.getName(),
            self._me.getMsgID(), len(rawMessage), rawMessage
        ).encode("ascii")
        self._observer.update(
            (OBSERVE_MESSAGE, rawMessage, self._me.getName()))
        self._broadcast([], message)

    def shutdown(self):
        self._connectionKeeper.shutdown()
        self._peerListener.shutdown()
        if self._forward:
            self._forward.shutdown()
        for handler in self._backward.values():
            handler.shutdown()


class NetworkManager(Thread):
    """
    NetworkManager is a class that actually handles all networking requests
    from other threads.
    """

    def __init__(self, observer, server):
        Thread.__init__(self)
        self._quitable = Event()
        self._queue = Queue()
        self._peer = PeerManager(self, observer)
        self._server = ServerManager(self, server, observer)

    def run(self):
        """
        On start, first it tries to connect to other peers.ACCEPT
        Then it indicates that it is OK to quit. This thread will
        wait for tasks to be submitted by other threads and execute them
        sequentially.
        """
        self._peer.connect()
        self._quitable.set()
        while True:
            item = self._queue.get()
            if item is None:
                print("starting shutting down")
                self._server.shutdown()
                self._peer.shutdown()
                break
            elif item[0] == ACCEPT:
                self._peer.accept(item[1])
            elif item[0] == RECEIVE:
                self._peer.receive(item[1], item[2])
            elif item[0] == CONNECT:
                self._peer.connect()
            elif item[0] == DISCONNECT:
                self._peer.disconnect(item[1])
            elif item[0] == KEEP_ALIVE:
                self._server.keepAlive()
            elif item[0] == SEND:
                self._peer.doSend(item[1])
            elif item[0] == DO_LIST:
                self._server.doList()

    def doList(self, joined):
        """
        If this peer has joined, submit to NetworkManager itself.
        Otherwise call doList directly.
        """
        if joined:
            self.submit((DO_LIST))
        else:
            self._server.doList()

    def doJoin(self, name, room, port, soc):
        """
        Setup ServerManager and PeerManager.ACCEPT
        And start running and accepting requests
        """
        ip = self._server.getIP()
        self._server.doJoin(name, room, port)
        self._peer.doJoin(name, room, ip, port, soc)
        self._running = True
        self.start()

    def doSend(self, message):
        self.submit((SEND, message))

    def shutdown(self, joined):
        """
        If this peer has Joined, wait until it is OK to quit,
        And submit quit request. Otherwise, shutdown ServerManager
        """
        if joined:
            self._quitable.wait()
            self.submit(None)
        else:
            self._server.shutdown(False)

    def keepAlive(self):
        """
        keepAlive and postpone AliveKeeper
        """
        self._server.keepAlive(True)

    def getMembers(self):
        return self._server.getMembers()

    def getMember(self, ID):
        return self._server.getMember(ID)

    def submit(self, item):
        """
        Submit a task into queue. All tasks will be executed sequentially
        """
        self._queue.put(item)


class P2PChat(object):
    """
    This class is an general interface for NetworkManager.
    It handles all state related exceptions and pushes requests
    down to NetworkManager if no Exception is raised
    """

    def __init__(self, server, port, observer=None):
        self._state = START_STATE
        self._name = None
        self._port = port
        self._s = socket.socket()
        try:
            self._s.bind(("", port))
        except OSError as e:
            print(e)
            sys.exit(-1)
        self._manager = NetworkManager(observer, server)

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
        self._manager.doJoin(self._name, room, self._port, self._s)
        self._state = JOINED_STATE

    def doList(self):
        if self._state == JOINED_STATE:
            self._manager.doList(True)
        else:
            self._manager.doList(False)

    def doQuit(self):
        if self._state == JOINED_STATE:
            self._manager.shutdown(True)
        else:
            self._manager.shutdown(False)

    def doSend(self, message):
        if self._state < JOINED_STATE:
            raise UnjoinedException()
        self._manager.doSend(message)

    def doUser(self, username):
        if self._state > NAMED_STATE:
            raise JoinedException()
        self._name = username
        self._state = NAMED_STATE


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
        """
        Check validity of information and handles illegal transitions
        """
        message = self.userentry.get()
        if len(message) > 0:
            try:
                self._chat.doSend(message)
            except UnjoinedException:
                self._cmd("[ERROR] Cannot send before JOIN")
            except RemoteException:
                self._cmd("[ERROR] " + e)
            self.userentry.delete(0, END)

    def do_Join(self):
        """
        Validate the input, and call P2PChat's do_Join.
        Handle exception and print errors.
        """
        room = self.userentry.get()
        if room:
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
        self._chat.doList()

    def do_User(self):
        """
        Validate the input, and call P2PChat's do_User.
        Handle exception and print errors.
        """
        username = self.userentry.get()
        if username:
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

    def _msg(self, sender, message):
        self.MsgWin.insert(1.0, "\n{}:{}".format(sender, message))

    def _valid(self, name):
        """
        Validate information
        """
        return all(map((lambda x: x != ':'), name))

    def update(self, message):
        """
        Print updated information.
        """
        if message[0] == OBSERVE_ADD:
            for i in message[1]:
                self._cmd(i)
            if self._first:
                self._cmd("[ROOM] List all members:")
                self._first = False
            else:
                self._cmd("[ROOM] user(s) joined:")
        elif message[0] == OBSERVE_REMOVE:
            for i in message[1]:
                self._cmd(i)
            self._cmd("[ROOM] user(s) left:")
        elif message[0] == OBSERVE_MESSAGE:
            self._msg(message[2], message[1])
        elif message[0] == OBSERVE_ERROR:
            self._cmd(message[1])
        elif message[0] == OBSERVE_FORWARD:
            self._cmd("[FORWARD] connected to {}".format(message[1]))
        elif message[0] == OBSERVE_BACKWARD:
            self._cmd("[BACKWARD] {} connected to you".format(message[1]))
        elif message[0] == OBSERVE_LIST:
            if not message[1]:
                self._cmd("[LIST] No chatroom available")
            else:
                for i in message[1]:
                    self._cmd(i)
                self._cmd("[LIST] list all chatroom(s)")


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)
    P2PChatUI(sys.argv)


if __name__ == "__main__":
    main()
