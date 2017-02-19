#!/usr/bin/python3

# Student name and No.: CHEN Zhihan, 3035142261
# Development platform: Ubuntu 16.04 64 bit
# Python version: Python 3.5.2
# Version:


from tkinter import *
import sys
import socket
from threading import Thread
from time import sleep
#
# Global variables
#
#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address),
# and str(Port) to form the input to this hash function
#

START_STATE = 0
NAMED_STATE = 1
JOINED_STATE = 2
CONNECTED_STATE = 3
TERMINATED_STATE = 4

class ListException(Exception):
    def __init__(self, msg):
        self.msg = msg


class UnnamedException(Exception):
    pass


class JoinedException(Exception):
    pass


class JoinException(Exception):
    def __init__(self, msg):
        self.msg = msg


def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


class Member(object):
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip[0]
        self.port = port


class AliveKeeper(Thread):
    def __init__(self, P2PChat):
        Thread.__init__(self)
        self.P2PChat = P2PChat

    def run(self):
        while self.P2PChat.state != TERMINATED_STATE:
            sleep(20)
            self.P2PChat.doJoin(self.P2PChat.room)


class P2PChat(object):
    def __init__(self, argv):
        self.port = int(argv[3])
        self.forward = None
        self.backwards = []
        self.username = None
        self.room = None
        self.members = ("", [])
        self.id = None
        self.roomServer = None
        self._connect((argv[1], int(argv[2])))
        self.state = START_STATE
        self.aliveKeeper = None

    def _connect(self, roomServer):
        self.roomServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.roomServer.connect(roomServer)

    def _request(self, message):
        message += "::\r\n"
        self.roomServer.send(message.encode("ascii"))
        print("{} sent to room server".format(message))
        done = False
        received = ""
        while not done:
            m = self.roomServer.recv(1024)
            received += m.decode("ascii")
            if len(received) > 4 and received[-4:] == "::\r\n":
                done = True
        print("{} received from room server".format(received))
        return received[:-4]

    def _parseJoin(self, message):
        result = message.split(':')
        MSID = result[0]
        if self.members[0] != MSID:
            members = []
            i = 1
            while i != len(result):
                members.append(Member(result[i], result[i + 1], int(result[i + 2])))
                i += 3
            self.members = (MSID, members)
        return self.members[1]

    def doList(self):
        message = self._request("L")
        if message[0] == 'F':
            raise ListException(message[2:])
        if len(message) == 1:
            return []
        else:
            return message[2:].split(':')

    def doUser(self, name):
        if self.state < 2:
            self.username = name
            self.state = NAMED_STATE
            return True
        else:
            raise JoinedException()

    def doJoin(self, room):
        if self.state >= 1:
            request = "J:{}:{}:{}:{}".format(room, self.username,
                                             self.roomServer.getsockname(),
                                             self.port)
            message = self._request(request)
            if message[0] == 'F':
                raise JoinException(message[2:])
            else:
                result = self._parseJoin(message[2:])
                self.room = room
                if self.aliveKeeper is None:
                    self.state = JOINED_STATE
                    self.aliveKeeper = AliveKeeper(self)
                    self.aliveKeeper.start()
                return result
        else:
            raise UnnamedException()

    def doQuit(self):
        self.state = TERMINATED_STATE
        if self.aliveKeeper is not None:
            self.aliveKeeper.join()


class P2PChatUI(object):
    def __init__(self, argv):
        self.chat = P2PChat(argv)
        #
        # Set up of Basic UI
        #
        win = Tk()
        win.title("MyP2PChat")

        # Top Frame for Message display
        topframe = Frame(win, relief=RAISED, borderwidth=1)
        topframe.pack(fill=BOTH, expand=True)
        topscroll = Scrollbar(topframe)
        self.MsgWin = Text(topframe, height='15', padx=5, pady=5,
                           fg="red", exportselection=0, insertofftime=0)
        self.MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
        topscroll.pack(side=RIGHT, fill=Y, expand=True)
        self.MsgWin.config(yscrollcommand=topscroll.set)
        topscroll.config(command=self.MsgWin.yview)

        # Top Middle Frame for buttons
        topmidframe = Frame(win, relief=RAISED, borderwidth=1)
        topmidframe.pack(fill=X, expand=True)
        Butt01 = Button(topmidframe, width='8', relief=RAISED,
                        text="User", command=self.do_User)
        Butt01.pack(side=LEFT, padx=8, pady=8)
        Butt02 = Button(topmidframe, width='8', relief=RAISED,
                        text="List", command=self.do_List)
        Butt02.pack(side=LEFT, padx=8, pady=8)
        Butt03 = Button(topmidframe, width='8', relief=RAISED,
                        text="Join", command=self.do_Join)
        Butt03.pack(side=LEFT, padx=8, pady=8)
        Butt04 = Button(topmidframe, width='8', relief=RAISED,
                        text="Send", command=self.do_Send)
        Butt04.pack(side=LEFT, padx=8, pady=8)
        Butt05 = Button(topmidframe, width='8', relief=RAISED,
                        text="Quit", command=self.do_Quit)
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

    def _writeCmd(self, msg):
        self.CmdWin.insert(1.0, "\n{}".format(msg))

    # Functions to handle user input

    def do_User(self):
        user = self.userentry.get()
        if len(user) > 0 and all(map((lambda x: x != ':'), user)):
            try:
                self.chat.doUser(user)
            except JoinedException:
                self._writeCmd("JOINED ALready")
            else:
                outstr = "\n[User] username: "+self.userentry.get()
                self.CmdWin.insert(1.0, outstr)
        else:
            self._writeCmd("incorrect username")
        self.userentry.delete(0, END)

    def do_List(self):
        try:
            l = self.chat.doList()
        except ListException as e:
            self._writeCmd(e.msg)
        else:
            for room in l:
                self._writeCmd(room)
            self._writeCmd("List all rooms:")

    def do_Join(self):
        room = self.userentry.get()
        if len(room) != 0:
            try:
                result = self.chat.doJoin(room)
            except UnnamedException:
                self._writeCmd("unnamed!")
            except JoinException as e:
                self._writeCmd("[Error]{}".format(e.msg))
            self.userentry.delete(0, END)
        else:
            self._writeCmd("Empty room name")

    def do_Send(self):
        self.CmdWin.insert(1.0, "\nPress Send")

    def do_Quit(self):
        self.CmdWin.insert(1.0, "\nPress Quit")
        self.chat.doQuit()
        sys.exit(0)


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)

    UI = P2PChatUI(sys.argv)

if __name__ == "__main__":
    main()
