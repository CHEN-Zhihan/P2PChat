import ctypes
from tkinter import *


class P2PChatUI(object):
    def __init__(self, argv):
        #
        # Set up of Basic UI
        #
        # self._chat = P2PChat((argv[1], int(argv[2])), int(argv[3]), self)
        self._chat = ctypes.CDLL("./P2PChat.so")
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
