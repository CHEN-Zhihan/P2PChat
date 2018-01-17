#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H
#include <pthread.h>
#include <semaphore.h>
#include <stdbool.h>
#include "network.h"

#include "peer_manager.h"
#include "server_manager.h"

struct alive_keeper_t {
    char* join_msg;
    bool running;
    int local_client;
    sem_t timeout;
    pthread_t monitor;
};

struct network_manager_t {
    struct socket_handler_t server;
    struct peer_manager_t peer;
    struct socket_handler_t local;
    struct alive_keeper_t alive_keeper;
    char* room;
    int local_server;
    int local_client;
    vector_peer_t peers;
    pthread_t event_handler;
};

void setup_network(struct network_manager_t*, char*, char*, int, int);
void setup_keep_alive(struct network_manager_t*, char*, int);
void network_manager_do_quit(struct network_manager_t*);
void network_manager_do_send(struct network_manager_t*, char*);

#endif  // NETWORK_MANAGER_H
