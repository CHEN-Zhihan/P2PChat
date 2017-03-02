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


class AliveKeeper(Thread):
    def __init__(self, manager):
        Thread.__init__(self)
        self._manager = manager
        self._running = True
        self._condition = Condition()

    def run(self):
        while self._running:
            self._manager.put(0)
            self._condition.acquire()
            self._condition.wait()
            self._condition.release()

    def shutdown(self):
        self._running = False
        self._condition.acquire()
        self._condition.notify()
        self._condition.release()


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
    def __init__(self, P2PChat):
        Thread.__init__(self)
        self.chat = P2PChat
        self.queue = Queue(maxsize=5)

    def run(self):
        pass

    def doJoin(self):
        pass

    def connect(self):
        pass

    def shutdown(self):
        pass

    def put(self, message):
        pass


class P2PChat(object):
    def __init__(self, argv, observer):
        self.server = (argv[0], int(argv[1]))
        self.port = int(argv[2])
        self.state = START_STATE

    def receive(self, message):
        pass

    def do_Join(self):
        pass

    def do_List(self):
        pass

    def do_Quit(self):
        pass

    def do_Send(self, message):
        pass

    def do_User(self, message):
        pass


class P2PChatUI(object):
    def __init__(self, argv):
        #
        # Set up of Basic UI
        #
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
        self.CmdWin.insert(1.0, "\nPress Quit")
        sys.exit(0)

    def do_Send(self):
        self.CmdWin.insert(1.0, "\nPress Send")

    def do_Join(self):
        self.CmdWin.insert(1.0, "\nPress JOIN")

    def do_List(self):
        self.CmdWin.insert(1.0, "\nPress List")

    def do_User(self):
        outstr = "\n[User] username: " + self.userentry.get()
        self.CmdWin.insert(1.0, outstr)
        self.userentry.delete(0, END)


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)
    P2PChatUI(sys.argv)


if __name__ == "__main__":
    main()
