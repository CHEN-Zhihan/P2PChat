#ifndef LOCAL_SERVER_H
#define LOCAL_SERVER_H

#include <semaphore.h>
#include "chat.h"

#define MAX_EVENTS 20

int setup_local_server(struct server_t*, int);
void connect_to_server(struct server_t*, const char*, int);
int connect_to_peers(struct server_t*, char*);
int start_keep_alive(struct server_t*, int, char*);
void sync_request(int, char*, char*);
void async_request(int, char*);

struct server_t {
    int local_server_soc;
    char local_server_buffer[BUFFER_SIZE];
    int peer_server_soc;
    char peer_server_buffer[BUFFER_SIZE];
    char server_buffer[BUFFER_SIZE];
    int server_soc;
    int epoll;
    bool running;
    pthread_t event_thread;
    pthread_t keep_alive_thread;
    sem_t keep_alive_sem;
    vector_member members;
    vector_peer backwards;
    int forward_soc;
    long my_hash_id;
};

#endif  // LOCAL_SERVER_H
