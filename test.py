from p2p import P2PChat
from time import sleep


class Observer(object):
    def __init__(self):
        pass

    def update(self, message):
        print(message)


def test():
    o = Observer()
    p2pList = []
    for i in range(10):
        p2pList.append(P2PChat(("localhost", 32340), 2000 + i, o))
    for i in range(10):
        p2pList[i].doUser(str(i))
        p2pList[i].doJoin("HW311")
        p2pList[i].doSend("my name is {}".format(i))
    for i in range(10):
        p2pList[i].doQuit()
    result = []
    for i in range(10):
        result.append(P2PChat(("localhost", 32340), 5000 + i, o))
        result[i].doUser(str(i + 20))
        result[i].doJoin("HW311")
        result[i].doSend("my name is {}".format(i))
    for i in range(10):
        result[i].doQuit()


if __name__ == "__main__":
    test()
