from tkinter import *
import sys
import socket
from threading import Thread, Condition, Lock
from Peer import PeerManager
from Server import ServerManager
from queue import Queue

START_STATE = 0
NAMED_STATE = 1
JOINED_STATE = 2
CONNECTED_STATE = 3

KEEP_ALIVE = "KEEP_ALIVE"
CONNECT = "CONNECT"

ADD = 1
REMOVE = 2
FORWARD = 3
BACKWARD = 4
MESSAGE = 5


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

    def getHost(self):
        return (self._ip, self._port)

    def __str__(self):
        return "{}@{}".format(self._name, self.getHost())

    def setMsgID(self, msgID):
        self._msgID = msgID

    def getMsgID(self):
        return self._msgID


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
        self._joinMessage = None

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

    def _connect(self):
        if self._forward is None:
            self._keepAlive()
            length = len(self._members)
            if length != 1:
                IDs = sorted(self._members.keys())
                myID = self._me.getID()
                i = (IDs.index(myID) + 1) % length
                while IDs[i] != myID:
                    if IDs[i] not in self._backward:
                        try:
                            forward = socket.socket()
                            forward.connect(self._members[IDs[i]].getHost())
                        except Exception as e:
                            print("[Peer Manager] Error connecting to ",
                                  members[IDs[i]], e)
                            del. forward
                        else:
                            result = self._handshake(forward)
                            if result >= 0:
                                self._addForward(self._members[IDs[i]],
                                                 result, forward)
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

    def _handshake(self, soc):
        result = False
        message = "P" + self._joinMessage[1:] + ":{}\r\n".format(
            self._me.getMsgID()
        )
        soc.settimeout(10)
        soc.send(message.encode("ascii"))
        try:
            received = soc.recv(1024).decode("ascii")
        except socket.timeout:
            print("[ERROR] Handshake timeout, delete ", soc.getpeername())
            return -1
        else:
            if received[:2] != "S:" or received[-4:] != "::\r\n":
                print("[ERROR] Incorrect handshake confirmation", received)
                return -1
        soc.settimeout(None)
        return int(received[2:-4])

    def _accept(self, soc):
        pass

    def _addForward(self, member, msgID, soc):
        m = member
        m.setMsgID(msgID)
        self._forward = PeerHandler(self, soc, m)
        self._forward.start()
        print("[Peer Manager] Add forward Link to ", m.getName())

    def _addBackward(self, member, msgID, soc):
        member.setMsgID(msgID)
        soc.send("S:{}::\r\n".format(self._me.getMsgID()).encode("ascii"))
        temp = PeerHandler(self, soc, m)
        self._backwards[member.getID()] = temp
        temp.start()
        print("[Peer Manager] Add Backward Link to ", m.getName())

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

    def _keepAlive(self):
        received = self._request(self._joinMessage)
        if received[0] == "F":
            self._observer.update((REMOTE_ERROR, received[2:]))
        else:
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

    def run(self):
        self._aliveKeeper.start()
        self._connectionKeeper.start()
        self._peerListener.start()
        self._connect()
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
        self._aliveKeeper.shutdown()
        self._connectionKeeper.shutdown()
        self._peerListener.shutdown()

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
        self._me = Member(name, ip, port)
        self._joinMessage = "J:{}:{}:{}:{}".format(
            room, name, ip, port
        )
        self._aliveKeeper = AliveKeeper(self)
        self._connectionKeeper = ConnectionKeeper(self)
        self._peerListener = PeerListener(self, (ip, port))
        self.start()

    def doSend(self, message):
        pass

    def shutdown(self):
        pass


class P2PChat(object):
    def __init__(self, server, port, observer=None):
        self._state = START_STATE
        self._name = None
        self._port = port
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
        self._manager.doJoin(self._name, room, self._port)
        self._state = JOINED_STATE

    def doList(self):
        return self._manager.doList()

    def doQuit(self):
        self._manager.doQuit()

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
        message = self.userentry.get()
        if len(message) > 0:
            try:
                self._chat.doSend(message)
            except UnjoinedException:
                self._cmd("[ERROR] Cannot send before JOIN")
            except RemoteException:
                self._cmd("[ERROR] " + e)
            else:
                self._msg(self._chat.getName(), message)
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