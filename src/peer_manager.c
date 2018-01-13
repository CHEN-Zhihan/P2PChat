#include "peer_manager.h"

void setup_peer_server(struct peer_manager_t* peer, char* local_ip, int port) {
    peer->handler.fd = get_server_socket(local_ip, port);
}
