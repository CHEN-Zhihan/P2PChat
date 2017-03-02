#!/usr/bin/python3

# Student name and No.:
# Student name and No.:
# Development platform:
# Python version:
# Version:


from tkinter import *
import sys
import socket
from threading import Thread, Condition
from queue import Queue

#
# Global variables
#
START_STATE = 0
NAMED_STATE = 1
JOINED_STATE = 2
CONNECTED_STATE = 3
DO_JOIN = 0
INITIAL_LIST = 0
ADD = 1
REMOVE = 2
#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address),
# and str(Port) to form the input to this hash function
#


def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


class UnnamedException(Exception):
    pass


class UnjoinedException(Exception):
    pass


class JoinedException(Exception):
    pass


class RemoteException(Exception):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


class Member(object):
    def __init__(self, name, ip, port):
        self._name = name
        self._ip = ip
        self._port = port
        self._msgID = 0
        self._ID = sdbm_hash("{}{}{}".format(name, ip, port))

    def getID(self):
        return self._ID

    def getName(self):
        return self._name


class AliveKeeper(Thread):
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True
        self._condition = Condition()

    def run(self):
        while self._running:
            self._manager.put(DO_JOIN)
            self._condition.acquire()
            self._condition.wait(20)
            self._condition.release()

    def shutdown(self):
        self._running = False
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()
        self.join()


class PeerListener(Thread):
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True

    def run(self):
        pass

    def shutdown(self):
        pass


class PeerHandler(Thread):
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True

    def run(self):
        pass

    def shutdown(self):
        pass


class NetworkManager(Thread):
    def __init__(self, P2PChat, roomServer, port):
        Thread.__init__(self)
        self._members = {}
        self._chat = P2PChat
        self._queue = Queue(maxsize=5)
        self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSocket.connect(roomServer)
        self._localhost = self._serverSocket.getsockname()[0]
        self._port = port
        self._aliveKeeper = AliveKeeper(self)
        self._forward = None
        self._backwards = []
        self._MSID = ""

    def _request(self, message):
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
            added = [temp[m].getName() for m in temp if m not in self._members]
            removed = [self._members[m].getName() for m in self._members if m not in temp]
            self._members = temp
            if added:
                self._chat.update((ADD, added))
            if removed:
                self._chat.update((REMOVE, removed))

    def run(self):
        while True:
            item = self._queue.get()
            if item is None:
                break
            if item == DO_JOIN:
                self._doJoin()

    def do_Join(self):
        self._aliveKeeper.start()

    def _doJoin(self):
        request = "J:{}:{}:{}:{}".format(self._room, self._name,
                                         self._localhost, self._port)
        received = self._request(request)
        if received[0] == 'F':
            raise RemoteException(received[1:])
        self._parseJoin(received[2:])

    def connect(self):
        pass

    def shutdown(self):
        self._serverSocket.close()
        self.put(None)
        if self._aliveKeeper.is_alive():
            self._aliveKeeper.shutdown()
        self.join()

    def put(self, message):
        self._queue.put(message)

    def do_List(self):
        received = self._request("L")
        if received[0] == 'F':
            raise RemoteException(received[2:])
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        return result

    def setInfo(self, name, room):
        self._name = name
        self._room = room


class P2PChat(object):
    def __init__(self, argv, observer):
        self._state = START_STATE
        self._name = None
        self._manager = NetworkManager(self,
                                       (argv[1], int(argv[2])), int(argv[3]))
        self._manager.start()
        self._observer = observer

    def receive(self, message):
        pass

    def do_Join(self, roomname):
        if self._state >= JOINED_STATE:
            raise JoinedException()
        if self._state == START_STATE:
            raise UnnamedException()
        self._manager.setInfo(self._name, roomname)
        self._manager.do_Join()
        self._room = roomname
        self._state = JOINED_STATE

    def do_List(self):
        return self._manager.do_List()

    def do_Quit(self):
        self._manager.shutdown()

    def do_Send(self, message):
        pass

    def do_User(self, message):
        if self._state > NAMED_STATE:
            raise JoinedException()
        self._name = message
        self._state = NAMED_STATE

    def update(self, l):
        self._observer.update(l)


class P2PChatUI(object):
    def __init__(self, argv):
        #
        # Set up of Basic UI
        #
        self._chat = P2PChat(argv, self)
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
        self._chat.do_Quit()
        sys.exit(0)

    def do_Send(self):
        self.CmdWin.insert(1.0, "\nPress Send")

    def do_Join(self):
        room = self.userentry.get()
        if self._valid(room):
            try:
                self._chat.do_Join(room)
            except JoinedException:
                self._cmd("[ERROR] Cannot join another room")
            except UnnamedException:
                self._cmd("[ERROR] Cannot join without name")
        else:
            self._cmd("[ERROR] Invalid roomname")
        self.userentry.delete(0, END)

    def do_List(self):
        try:
            result = self._chat.do_List()
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
        username = self.userentry.get()
        if self._valid(username):
            try:
                self._chat.do_User(username)
            except JoinedException:
                self._cmd("[ERROR] Cannot Rename after Join")
            else:
                self._cmd("[USER] username: " + username)
        else:
            self._cmd("[ERROR] Invalid username")
        self.userentry.delete(0, END)

    def _cmd(self, message):
        self.CmdWin.insert(1.0, "\n" + message)

    def _valid(self, name):
        return len(name) != 0 and all(map((lambda x: x != ':'), name))

    def update(self, message):
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
