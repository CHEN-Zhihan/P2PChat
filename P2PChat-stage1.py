#!/usr/bin/python3

# Student name and No.: CHEN Zhihan, 3035142261
# Development platform: Ubuntu 16.04 64 bit
# Python version: Python 3.5.2
# Version: 1.0


from tkinter import *
import sys
import socket
from threading import Thread, Condition, Lock
from concurrent.futures import ThreadPoolExecutor
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
        self.ip = ip.split(',')[0][1:]
        self.port = port


class AliveKeeper(Thread):
    def __init__(self, P2PChat):
        Thread.__init__(self)
        self.P2PChat = P2PChat
        self.condition = Condition()

    def run(self):
        while self.P2PChat.state != TERMINATED_STATE:
            self.P2PChat.doJoin(self.P2PChat.room)
            self.condition.acquire()
            self.condition.wait(timeout=20)
            self.condition.release()

    def shutdown(self):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()


class ServerListener(Thread):
    def __init__(self, P2PChat, socket):
        Thread.__init__(self)
        self.P2PChat = P2PChat
        self.socket = socket

    def run(self):
        while self.P2PChat.state != TERMINATED_STATE:
            done = False
            received = ""
            while self.P2PChat.state != TERMINATED_STATE and not done:
                m = self.socket.recv(1024)
                received += m.decode("ascii")
                if len(received) > 4 and received[-4:] == "::\r\n":
                    done = True
                    self.P2PChat.receive(received[:-4])


class P2PChat(object):
    def __init__(self, argv, observer):
        self.port = int(argv[3])
        self.tempRoom = None
        self.forward = None
        self.backwards = []
        self.username = None
        self.room = None
        self.members = ("", [])
        self.id = None
        self.host = (argv[1], int(argv[2]))
        self.roomServer = None
        self.aliveKeeper = None
        self.observer = observer
        self.roomServerListener = None
        self.state = START_STATE

    def _send(self, message):
        message += "::\r\n"
        self.roomServer.send(message.encode("ascii"))
        print("{} sent to room server".format(message))

    def _parseJoin(self, message):
        result = message.split(':')
        MSID = result[0]
        modified = self.members[0] != MSID
        if modified:
            members = []
            i = 1
            while i != len(result):
                members.append(Member(result[i],
                               result[i + 1], int(result[i + 2])))
                i += 3
            self.members = (MSID, members)
        return (modified, self.members[1])

    def _connect(self):
        if self.roomServer is None:
            try:
                self.roomServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.roomServer.connect(self.host)
                self.roomServerListener = ServerListener(self, self.roomServer)
                self.roomServerListener.start()
            except Exception as e:
                print(e)
                sys.exit(-1)

    def receive(self, message):
        flag = message[0]
        if flag == 'G':
            self._receiveList(message)
        elif flag == 'F':
            self._error(message)
        elif flag == 'M':
            self._receiveJoin(message)

    def doList(self):
        self._connect()
        self._send("L")

    def _receiveList(self, message):
        result = []
        if len(message) != 1:
            result = message[2:].split(':')
        self.observer.updateList(result)

    def doUser(self, name):
        if self.state < 2:
            self.username = name
            self.state = NAMED_STATE
            return True
        else:
            raise JoinedException()

    def doJoin(self, room):
        self._connect()
        request = "J:{}:{}:{}:{}".format(room, self.username,
                                         self.roomServer.getsockname(),
                                         self.port)
        self._send(request)
        self.tempRoom = room

    def _error(self, message):
        self.observer.error(message[2:])

    def _receiveJoin(self, message):
        result = self._parseJoin(message[2:])
        if self.aliveKeeper is None:
            self.room = self.tempRoom
            self.state = JOINED_STATE
            self.aliveKeeper = AliveKeeper(self)
            self.aliveKeeper.start()
        if result[0]:
            self.observer.updateJoin(result[1])

    def doQuit(self):
        self.state = TERMINATED_STATE
        if self.aliveKeeper is not None:
            self.aliveKeeper.shutdown()
            self.aliveKeeper.join()
        if self.roomServer is not None:
            self.roomServer.shutdown(socket.SHUT_RDWR)
            self.roomServer.close()
            self.roomServerListener.join()


class P2PChatUI(object):
    def __init__(self, argv):
        self.chat = P2PChat(argv, self)
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

    def error(self, message):
        self._writeCmd("[Error] {}".format(message))

    # Functions to handle user input

    def do_User(self):
        user = self.userentry.get()
        if len(user) > 0 and all(map((lambda x: x != ':'), user)):
            try:
                self.chat.doUser(user)
            except JoinedException:
                self.error("Cannot rename after JOINED")
            else:
                self._writeCmd("[User] username: {}".format(
                                                        self.userentry.get()))
        else:
            self.error("Incorrect Username")
        self.userentry.delete(0, END)

    def do_List(self):
        l = self.chat.doList()

    def updateList(self, l):
        for room in l:
            self._writeCmd(room)
        self._writeCmd("[List]List all rooms:")

    def do_Join(self):
        room = self.userentry.get()
        if len(room) != 0 and all(map((lambda x: x != ':'), room)):
            if self.chat.state == START_STATE:
                self.error("Cannot join before NAMED")
            elif self.chat.state == NAMED_STATE:
                self.chat.doJoin(room)
            elif self.chat.state >= JOINED_STATE:
                self.error("Joined in a chatroom already")
        else:
            self.error("Invalid roomname")
        self.userentry.delete(0, END)

    def updateJoin(self, l):
        for member in l:
            self._writeCmd(member.name)
        self._writeCmd("[Info] Member list updated")

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
