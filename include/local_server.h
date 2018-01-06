#ifndef LOCAL_SERVER_H
#define LOCAL_SERVER_H

#include "chat.h"

#define MAX_EVENTS 20

int setup_local_server(struct server_t*, int);
void connect_to_server(struct server_t*, const char*, int);
void sync_request(int, char*, char*);
void async_request(int, char*);
#endif  // LOCAL_SERVER_H
