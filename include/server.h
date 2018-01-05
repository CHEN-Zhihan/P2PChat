#ifndef SERVER_H
#define SERVER_H
#include <netinet/in.h>
#include <pthread.h>
#include <stdbool.h>
#include "chat.h"

#define nullptr NULL
#define BUFFER_SIZE 1024
void set_server_address(const char*, int, int);
void connect_to_server();
bool connected();
void setup_server();
vector_str request_do_list();

char* request(const char*, int socket);

void join();

typedef struct local_server {
    struct sockaddr_in serv_addr;
    int serv_soc;
    int local_soc;
    int local_port;
    bool joined;
    pthread_t loop;
    bool running;
    char* join_msg;
} local_server_t;

#endif  // SERVER_H
