#ifndef PEER_MANAGER_H
#define PEER_MANAGER_H
#include <stdbool.h>
#include "common.h"
#include "message.h"
#include "peer.h"

struct network_manager_t;

struct peer_manager_t {
    int server;
    struct connected_peer_t forward;
    char peer_buffer[BUFFER_SIZE];
    vector_connected_peer_t backwards;
    int msgid;
    long my_hash_id;
    char* partial_handshake_msg;
    char* partial_send_msg;
};

void setup_peer_server(struct peer_manager_t*, char*, int);
int connect_to_peer(struct peer_manager_t*, vector_peer_t);
void send_msg(struct peer_manager_t*, char*);
void close_connected_peers(struct peer_manager_t*);
int handle_new_peer(struct peer_manager_t*, struct network_manager_t*);
int handle_peer_message(struct peer_manager_t*, struct network_manager_t*, int);
bool is_member(vector_peer_t, long);
#endif  // PEER_MANAGER_H
