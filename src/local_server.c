#include "local_server.h"
#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdbool.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>
#include "chat.h"
#include "common.h"
#include "network.h"

sem_t semaphore;
pthread_mutex_t transit_mutex = PTHREAD_MUTEX_INITIALIZER;

void* event_loop(void*);
void start_local_server(struct server_t*);
void accept_new_socket(int, int);
void handle_socket(struct server_t*, int, int);
void handle_message(struct server_t*, char*, int);
void transit(int, char*, char*);

int setup_local_server(struct server_t* server, int port) {
    server->local_server_soc = get_server_socket("127.0.0.1", port);
    make_non_block(server->local_server_soc);
    sem_init(&semaphore, 0, 0);
    pthread_create(&server->event_thread, nullptr, &event_loop, (void*)server);
    sem_wait(&semaphore);
    int soc_fd = get_client_socket("127.0.0.1", port);
    return soc_fd;
}

void* event_loop(void* s) {
    struct server_t* server = (struct server_t*)s;
    int epoll_fd = epoll_create1(0);
    struct epoll_event event, events[MAX_EVENTS];
    handle_error(listen(server->local_server_soc, 0),
                 " listen to local socket failed");
    event.data.fd = server->local_server_soc;
    event.events = EPOLLIN | EPOLLET;
    handle_error(
        epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server->local_server_soc, &event),
        " add server socket to epoll failed");
    fprintf(stdout, "[INFO] entering event loop\n");
    sem_post(&semaphore);
    while (true) {
        int nb_of_available_sockets = 0, i = 0;
        nb_of_available_sockets = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        for (i = 0; i != nb_of_available_sockets; ++i) {
            uint32_t e = events[i].events;
            if (e & EPOLLERR || e & EPOLLHUP || !(e & EPOLLIN)) {
                handle_error(-1, "Epoll failed");
            } else if (server->local_server_soc == events[i].data.fd) {
                accept_new_socket(server->local_server_soc, epoll_fd);
            } else {
                handle_socket(server, epoll_fd, events[i].data.fd);
            }
        }
    }
}

void accept_new_socket(int local_server_soc, int epoll_fd) {
    while (true) {
        struct sockaddr_in addr;
        int new_fd;
        char host_buffer[NI_MAXHOST], serv_buffer[NI_MAXSERV];
        struct epoll_event event;
        uint32_t size = sizeof(addr);
        new_fd = accept(local_server_soc, (struct sockaddr*)&addr, &size);
        if (new_fd == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            break;
        }
        int result =
            getnameinfo((const struct sockaddr*)&addr, sizeof(addr),
                        host_buffer, sizeof(host_buffer), serv_buffer,
                        sizeof(serv_buffer), NI_NUMERICHOST | NI_NUMERICSERV);
        if (result == 0) {
            fprintf(stdout, "[INFO] accepted connection from %s:%s\n",
                    host_buffer, serv_buffer);
        }
        make_non_block(new_fd);
        event.data.fd = new_fd;
        event.events = EPOLLIN | EPOLLET;
        handle_error(epoll_ctl(epoll_fd, EPOLL_CTL_ADD, new_fd, &event),
                     "add to epoll failed");
    }
}

void handle_socket(struct server_t* server, int epoll_fd, int income_fd) {
    bool done = false;
    while (true) {
        ssize_t count =
            read(income_fd, server->local_server_buffer, BUFFER_SIZE);
        if (count == -1 && errno == EAGAIN) {
            break;
        }
        if (count == 0) {
            done = true;
            break;
        }
        handle_error(count, "read failed");
        handle_error(write(STDOUT_FILENO, server->local_server_buffer, count),
                     "write to stdout failed");
        handle_message(server, server->local_server_buffer, income_fd);
    }
    if (done) {
        fprintf(stdout, "[INFO] close FD %d\n", income_fd);
        close(income_fd);
    }
}

void connect_to_server(struct server_t* server, const char* serv_addr,
                       int serv_port) {
    server->server_soc = get_client_socket(serv_addr, serv_port);
    fprintf(stdout, "[INFO] connected to server %s:%d\n", serv_addr, serv_port);
}

void transit(int soc, char* msg, char* buffer) {
    pthread_mutex_lock(&transit_mutex);
    handle_error(write(soc, msg, strlen(msg)), "write to soc failed");
    read(soc, buffer, BUFFER_SIZE);
    pthread_mutex_unlock(&transit_mutex);
}

void handle_message(struct server_t* server, char* msg, int income_fd) {
    if (LAST(msg) == '\r') {
        LAST(msg) = '\n';
        transit(server->server_soc, msg, server->server_buffer);
        write(income_fd, server->server_buffer, strlen(server->server_buffer));
    }
}
