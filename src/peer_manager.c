#include "peer_manager.h"
#include <sys/socket.h>
#include <sys/types.h>
int handshake(struct peer_manager_t*, int);
bool is_member(vector_peer_t, long);
int get_index_by_fd(vector_connected_peer_t, int);
int get_last_msgid(vector_connected_peer_t, int);
void update_msgid(struct peer_manager_t*, ) bool is_backward(
    vector_connected_peer_t backwards, long hash_id) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].hash_id == hash_id) {
            return true;
        }
    }
    return false;
}

void setup_peer_server(struct peer_manager_t* peer, char* local_ip, int port) {
    peer->handler.fd = get_server_socket(local_ip, port);
}

int connect_to_peer(struct peer_manager_t* peer, vector_peer_t peers) {
    int i = 0;
    for (i = 0; i != peers.size; ++i) {
        if (peer->my_hash_id == peers.data[i].hash_id) {
            break;
        }
    }
    i = (i + 1) % peers.size;
    while (peer->my_hash_id != peers.data[i]) {
        if (!is_backward(peer->backwards, peers.data[i].hash_id)) {
            struct peer_t candidate = peers.data[i];
            int peer_soc = get_client_socket(candidate.ip, candidate.port);
            if (peer_soc > 0) {
                int result = handshake(peer, peer_soc);
                if (result >= 0) {
                    if (peer->forward.soc != 0) {
                        free_connected_peer(&peer->forward);
                    }
                    peer->forward =
                        get_connected_peer(candidate, peer_soc, result);
                    return peer_soc;
                }
            }
        }
        i = (i + 1) % peers.size;
    }
    return -1;
}

int handshake(struct peer_manager_t* peer, int soc) {
    char* handshake_msg =
        build_handshake_msg(peer->partial_handshake_msg, peer->msgid);
    char buffer[BUFFER_SIZE];
    sync_request(soc, handshake_msg, buffer);
    if (strlen(buffer) == 0) {
        return -1;
    }
    int msgid;
    sscanf(buffer, "S:%d::\r\n", &msgid);
    if (msgid > peer->msgid) {
        peer->msgid = msgid;
    }
    return msgid;
}

int handle_new_peer(struct peer_manager_t* peer,
                    struct network_manager_t* manager) {
    struct sockaddr_in addr;
    socklen_t size = sizeof(addr);
    int new_fd = accept(peer->server, &addr, &size, 0);
    char buffer[BUFFER_SIZE];
    read(new_fd, buffer, BUFFER_SIZE);
    struct handshake_t handshake_msg = parse_handshake(buffer);
    if (!strcmp(manager->room, handshake_msg.room)) {
        close(new_fd);
        free_peer(handshake_msg.peer);
        free(handshake_msg.room);
        return -1;
    }
    if (!is_member(manager->peers, handshake_msg.peer.hash_id)) {
        char* join_msg = strdup(manager->alive_keeper.join_msg);
        join_msg[0] = 'J';
        write(manager->server.fd, join_msg, strlen(manager->local.buffer));
        read(manager->server.fd, manager->server.buffer, BUFFER_SIZE);
        update_member_list(manager);
    }
    if (!is_member(manager->peers, handshake_msg.peer.hash_id)) {
        close(new_fd);
        free_peer(handshake_msg.peer);
        free(handshake_msg.room);
        return -1;
    }
    connected_peer_t p =
        get_connected_peer(handshake_msg.peer, new_fd, handshake_msg.msgid);
    VECTOR_STRUCT_PUSH_BACK(peer->backwards, connected_peer_t, p);
    return new_fd;
}

bool is_member(vector_peer_t peers, long id) {
    int i = 0;
    for (i = 0; i != peers.size; ++i) {
        if (peers.data[i].hash_id == id) {
            return true;
        }
    }
    return false;
}

int handle_peer_message(struct peer_manager_t* peer,
                        struct network_manager_t* manager, int fd) {
    read(fd, peer->peer_buffer, BUFFER_SIZE);
    if (strlen(peer->peer_buffer) == 0) {
        if (fd == peer->forward.soc) {
            close(fd);
            return connect_to_peer(peer, manager->peers);
        } else {
            int i = get_index_by_fd(peer->backwards, fd);
            VECTOR_ERASE(peer->backwards, i, free_connected_peer);
            return -1;
        }
    }
    struct message_t message = parse_message(peer->peer_buffer);
    struct connected_peer_t* sender = find_sender(peer, message.hash_id);
    int last_msgid = 0;
    if (fd == peer->forward.soc) {
        last_msgid = peer->forward.msgid;
    } else {
        last_msgid = get_last_msgid(peer->backwards, fd);
    }
    if (last_msgid > message.msgid) {
        return 0;
    }
    update_msgid(peer, fd, message.msgid);
    broadcast(peer, fd);
    callback_msg(message.name, message.content);
    free_message(message);
    return 0;
}

int get_index_by_id(vector_connected_peer_t backwards, int fd) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].soc == fd) {
            return i;
        }
    }
    return -1;
}

int get_last_msgid(vector_connected_peer_t backwards, int fd) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].soc == fd) {
            return backwards.data[i].msgid;
        }
    }
    return -1;
}
