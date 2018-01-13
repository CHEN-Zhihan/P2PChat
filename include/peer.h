#ifndef PEER_H
#define PEER_H
#include "vector.h"

struct peer_t {
    char* name;
    char* ip;
    int port;
};

struct connected_peer_t {
    struct peer_t peer;
    int soc;
};

USE_STRUCT_VECTOR(peer_t);
USE_STRUCT_VECTOR(connected_peer_t);

#endif  // PEER_H