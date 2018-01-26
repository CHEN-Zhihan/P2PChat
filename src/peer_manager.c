#include "peer_manager.h"
#include <ifaddrs.h>
#include <netinet/in.h>
#include <stdbool.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include "chat_wrapper.h"
#include "network.h"
#include "network_manager.h"
#include "parser.h"
int handshake(struct peer_manager_t*, int);
bool is_member(vector_peer_t, unsigned long);
int get_index_by_fd(vector_connected_peer_t, int);
int get_last_msgid(vector_connected_peer_t, int);
void broadcast(struct peer_manager_t*, int, unsigned long, char*);
bool is_backward(vector_connected_peer_t backwards, unsigned long hash_id) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].peer.hash_id == hash_id) {
            return true;
        }
    }
    return false;
}

void setup_peer_server(struct peer_manager_t* peer, char* local_ip, int port) {
    peer->server = get_server_socket(local_ip, port);
    VECTOR_INIT(peer->backwards);
}

int connect_to_peer(struct peer_manager_t* peer, vector_peer_t peers) {
    int i = 0;
    for (i = 0; i != peers.size; ++i) {
        if (peer->my_hash_id == peers.data[i].hash_id) {
            break;
        }
    }
    i = (i + 1) % peers.size;
    while (peer->my_hash_id != peers.data[i].hash_id) {
        if (!is_backward(peer->backwards, peers.data[i].hash_id)) {
            struct peer_t candidate = peers.data[i];
            fprintf(stderr, "[PEER] sending request to %s:%d\n", candidate.ip,
                    candidate.port);
            int peer_soc = get_client_socket(candidate.ip, candidate.port);
            if (peer_soc > 0) {
                int result = handshake(peer, peer_soc);
                if (result >= 0) {
                    if (peer->forward.soc != 0) {
                        free_connected_peer(&peer->forward);
                    }
                    peer->forward =
                        get_connected_peer(candidate, peer_soc, result);
                    fprintf(stderr, "[PEER] %s added as forward\n",
                            peers.data[i].name);
                    return peer_soc;
                }
                fprintf(stderr, "[DEBUG] handshake failed\n");
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
    int new_fd = accept(peer->server, nullptr, nullptr);
    char buffer[BUFFER_SIZE];
    fprintf(stderr, "[PEER] waiting for peer handshake\n");
    read(new_fd, buffer, BUFFER_SIZE);
    fprintf(stderr, "[PEER] peer handshake received *%s*\n", buffer);
    struct handshake_t handshake_msg = parse_handshake(buffer);
    if (strcmp(manager->room, handshake_msg.room)) {
        fprintf(stderr, "[DEBUG] Peer room incorrect\n");
        close(new_fd);
        free_peer(handshake_msg.peer);
        free(handshake_msg.room);
        return -1;
    }
    check_and_update(manager, handshake_msg.peer.hash_id);
    if (!is_member(manager->peers, handshake_msg.peer.hash_id)) {
        fprintf(stderr, "[DEBUG] not one of the member\n");
        close(new_fd);
        free_peer(handshake_msg.peer);
        free(handshake_msg.room);
        return -1;
    }
    struct connected_peer_t p =
        get_connected_peer(handshake_msg.peer, new_fd, handshake_msg.msgid);
    VECTOR_STRUCT_PUSH_BACK(peer->backwards, connected_peer_t, p);
    fprintf(stderr, "[PEER] %s added as backwards\n", handshake_msg.peer.name);
    char response[20];
    snprintf(response, 20, "S:%d::\r\n", peer->msgid);
    write(new_fd, response, strlen(response) + 1);
    free(handshake_msg.room);
    free_peer(handshake_msg.peer);
    return new_fd;
}

bool is_member(vector_peer_t peers, unsigned long id) {
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
    fprintf(stderr, "[PEER] receive *%s* from peer\n", peer->peer_buffer);
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
    check_and_update(manager, message.hash_id);
    struct peer_t* sender = find_peer(manager->peers, message.hash_id);
    if (sender == nullptr) {
        return 0;
    }
    if (sender->msgid > message.msgid) {
        return 0;
    }
    sender->msgid = message.msgid;
    broadcast(peer, fd, message.msgid, peer->peer_buffer);
    callback_msg(message.name, message.content);
    free_message(message);
    return 0;
}

int get_index_by_fd(vector_connected_peer_t backwards, int fd) {
    int i = 0;
    for (i = 0; i != backwards.size; ++i) {
        if (backwards.data[i].soc == fd) {
            return i;
        }
    }
    return -1;
}

void broadcast(struct peer_manager_t* peer, int fd, unsigned long hash_id,
               char* msg) {
    size_t length = strlen(msg) + 1;
    if (peer->forward.soc != fd && peer->forward.peer.hash_id != hash_id) {
        write(peer->forward.soc, msg, length);
    }
    int i = 0;
    for (i = 0; i != peer->backwards.size; ++i) {
        if (peer->backwards.data[i].soc != fd &&
            peer->backwards.data[i].peer.hash_id != hash_id) {
            write(peer->backwards.data[i].soc, msg, length);
        }
    }
}

void send_msg(struct peer_manager_t* peer, char* msg) {
    char* full_msg =
        build_send_msg(peer->partial_send_msg, ++peer->msgid, msg + 2);
    fprintf(stderr, "[DEBUG] full_msg:*%s*\n", full_msg);
    size_t length = strlen(full_msg) + 1;
    if (peer->forward.soc != 0) {
        fprintf(stderr, "[PEER] Send message to forward %s\n",
                peer->forward.peer.name);
        write(peer->forward.soc, full_msg, length);
    }
    int i = 0;
    for (i = 0; i != peer->backwards.size; ++i) {
        fprintf(stderr, "[PEER] Send message to backward %s\n",
                peer->backwards.data[i].peer.name);
        write(peer->backwards.data[i].soc, full_msg, length);
    }
    free(full_msg);
}
