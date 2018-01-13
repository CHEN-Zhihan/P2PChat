#ifndef PEER_MANAGER_H
#define PEER_MANAGER_H
#include "common.h"
#include "peer.h"
struct peer_manager_t {
    int server;
    struct connected_peer_t forward;
    char peer_buffer[BUFFER_SIZE];
    vector_connected_peer_t backwards;
    int msgid;
};

void setup_peer_server(struct peer_manager_t*, char*, int);
void handshake(struct peer_manager_t*, char*, vector_peer_t);
void send_msg(struct peer_manager_t*, char*);
void close_connected_peers(struct peer_manager_t*);
#endif  // PEER_MANAGER_H
