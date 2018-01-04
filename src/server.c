#include "server.h"
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
local_server_t server;
char buffer[BUFFER_SIZE];
sem_t server_ready;
void request_loop();
void setup_local_server();
void start_local_server();
int get_local_server();
char* request_server(char*);

bool connected() { return server.serv_soc != 0; }

void set_server_address(char* addr, int server_port, int port) {
    server.serv_soc = 0;
    server.serv_addr.sin_family = AF_INET;
    server.serv_addr.sin_port = htons(server_port);
    server.local_port = port + 1;
    server.local_soc = 0;
    if (inet_pton(AF_INET, addr, &server.serv_addr.sin_addr) <= 0) {
        fprintf(stderr, "[ERROR] inet_pton error %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
}

int setup_server() {
    connect_to_server();
    setup_local_server();
    start_local_server();
    return get_local_server();
}

void connect_to_server() {
    server.serv_soc = socket(AF_INET, SOCK_STREAM, SOCK_CLOEXEC);
    if (server.serv_soc < 0) {
        fprintf(stderr, "[ERROR] error opening socket");
        exit(EXIT_FAILURE);
    }
    if (connect(server.serv_soc, (struct sockaddr*)&server.serv_addr,
                sizeof(server.serv_addr)) < 0) {
        fprintf(stderr, "[ERROR] connect error %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
}

void setup_local_server() {
    server.local_soc = socket(AF_INET, SOCK_STREAM, SOCK_CLOEXEC);
    if (server.serv_soc < 0) {
        fprintf(stderr, "[ERROR] error opening socket");
        exit(EXIT_FAILURE);
    }
    struct sockaddr_in local_addr;
    local_addr.sin_family = AF_INET;
    local_addr.sin_port = htons(server.local_port);
    if (inet_pton(AF_INET, "127.0.0.1", &local_addr.sin_addr) <= 0) {
        fprintf(stderr, "[ERROR] inet_pton error %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
    if (bind(server.local_soc, (struct sockaddr*)&local_addr,
             sizeof(local_addr)) < 0) {
        fprintf(stderr, "[ERROR] cannot bind to local port %s\n",
                strerror(errno));
        exit(EXIT_FAILURE);
    }
}

void start_local_server() {
    sem_init(&server_ready, 0, 0);
    pthread_create(&server.loop, nullptr, request_loop, nullptr);
    sem_wait(&server_ready);
}

void request_loop() {
    if (listen(server.local_soc, 5) < 0) {
        fprintf(stderr, "[ERROR] cannot listen %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
    sem_post(&server_ready);
    int addr_size = sizeof(struct sockaddr_in);
    struct sockaddr_in peer_addr;
    int cfd = accept(server.serv_soc, (struct sockaddr*)&peer_addr,
                     sizeof(peer_addr));
    if (cfd < 0) {
        fprintf(stderr, "[ERROR] failed to accept local socket %s\n",
                strerror(errno));
        exit(EXIT_FAILURE);
    }
    char local_buffer[BUFFER_SIZE];
    struct timeval tv;
    tv.tv_sec = 20;
    setsockopt(cfd, SOL_SOCKET, SO_RCVTIMEO, (char*)&tv, sizeof(tv));
    while (server.running) {
        int n = recv(cfd, local_buffer, BUFFER_SIZE, 0);
        if (!server.running) {
            break;
        }
        char* result = nullptr;
        if (n == 0 && server.joined) {
            result = request_server(server.join_msg);
        } else {
            result = request_server(local_buffer);
        }
        if (send(cfd, result, strlen(result), 0) < 0) {
            fprintf(stderr, "[ERROR] cannot send back to local %s\n",
                    strerror(errno));
            exit(EXIT_FAILURE);
        }
    }
}

char* request_server(char* msg) {
    if (send(server.serv_soc, msg, strlen(msg), 0) < 0) {
        fprintf(stderr, "[ERROR] cannot send to server %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
    if (recv(server.serv_soc, buffer, BUFFER_SIZE, 0) < 0) {
        fprintf(stderr, "[ERROR] cannot receive from server %s\n",
                strerror(errno));
        exit(EXIT_FAILURE);
    }
    return buffer;
}

int get_local_server() {
    int result = socket(AF_INET, SOCK_STREAM, SOCK_CLOEXEC);
    struct sockaddr_in local_addr;
    struct sockaddr_in local_addr;
    local_addr.sin_family = AF_INET;
    local_addr.sin_port = htons(server.local_port);
    if (inet_pton(AF_INET, "127.0.0.1", &local_addr.sin_addr) <= 0) {
        fprintf(stderr, "[ERROR] inet_pton error %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
    if (connect(result, (struct sockaddr*)&local_addr, sizeof(local_addr)) <
        0) {
        fprintf(stderr, "[ERROR] connect error %s\n", strerror(errno));
        exit(EXIT_FAILURE);
    }
    return result;
}
