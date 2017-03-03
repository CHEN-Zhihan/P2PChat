from prototype import P2PChat
from time import sleep


def test():
    p2pList = []
    for i in range(20):
        p2pList.append(P2PChat(("147.8.91.103", 32340), 4000 + i, None))
    for i in range(20):
        p2pList[i].doUser(str(i))
        p2pList[i].doJoin("HW311")
    for i in range(20):
        p2pList[i].doQuit()
    result = []
    for i in range(20):
        result.append(P2PChat(("147.8.91.103", 32340), 3000 + i, None))
        result[i].doUser(str(i + 20))
        result[i].doJoin("HW311")
    for i in range(20):
        result[i].doQuit()


if __name__ == "__main__":
    test()
