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
        self._chat = P2PChat
        self._queue = Queue(maxsize=5)
        self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._serverSocket.connect(roomServer)
        self._aliveKeeper = None

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

    def run(self):
        while True:
            item = self._queue.get()
            if item is None:
                break

    def doJoin(self):
        pass

    def connect(self):
        pass

    def shutdown(self):
        self._serverSocket.close()
        self.put(None)
        if self._aliveKeeper is not None:
            self._aliveKeeper.shutdown()
        self.join()

    def put(self, message):
        self._queue.put(message)

    def do_List(self):
        received = self._request("L")
        result = []
        if len(received) != 1:
            result = received[2:].split(':')
        return result


class P2PChat(object):
    def __init__(self, argv, observer):
        self._state = START_STATE
        self._name = None
        self._room = None
        self._manager = NetworkManager(self,
                                       (argv[1], int(argv[2])), int(argv[3]))
        self._manager.start()

    def receive(self, message):
        pass

    def do_Join(self, roomname):
        pass

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

    def getRoom(self):
        return self._room


class P2PChatUI(object):
    def __init__(self, argv):
        #
        # Set up of Basic UI
        #
        self._chat = P2PChat(argv, self)
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
        self.CmdWin.insert(1.0, "\nPress JOIN")

    def do_List(self):
        result = self._chat.do_List()
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


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)
    P2PChatUI(sys.argv)


if __name__ == "__main__":
    main()
