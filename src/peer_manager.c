#include "peer_manager.h"

int handshake(struct peer_manager_t*, int);

bool is_backward(vector_connected_peer_t backwards, long hash_id) {
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
    sort_peers(&peers, 0, peers.size);
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
                    peer->forward = get_connected_peer(peer_soc, candidate);
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

int handle_new_peer(struct peer_manager_t* peer) { int }
