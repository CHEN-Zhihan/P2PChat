#include "local_server.h"
#include <errno.h>
#include <netdb.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdbool.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
#include "chat.h"
#include "common.h"
#include "network.h"
#include "peer.h"

sem_t semaphore;
pthread_mutex_t transit_mutex = PTHREAD_MUTEX_INITIALIZER;

void* event_loop(void*);
void* keep_alive(void*);
void start_local_server(struct server_t*);
void accept_new_socket(int, int);
void handle_socket(struct server_t*, int, int);
void handle_message(struct server_t*, char*, int);
void handle_local_request(struct server_t*);
void handle_do_join(struct server_t*, char*);
void sync_request(int, char*, char*);
int connect_to_peer(struct server_t*, member);
int handshake(struct server_t*, int, char*);
void add_to_listen(struct server_t*, int);

int setup_local_server(struct server_t* server, int port) {
    server->local_server_soc = get_server_socket("127.0.0.1", port + 1);
    server->peer_server_soc = get_server_socket("127.0.0.1", port);
    make_non_block(server->local_server_soc);
    make_non_block(server->peer_server_soc);
    sem_init(&semaphore, 0, 0);
    pthread_create(&server->event_thread, nullptr, &event_loop, (void*)server);
    sem_wait(&semaphore);
    int soc_fd = get_client_socket("127.0.0.1", port + 1);
    return soc_fd;
}

void* event_loop(void* s) {
    struct server_t* server = (struct server_t*)s;
    server->epoll = epoll_create1(0);
    struct epoll_event event, events[MAX_EVENTS];
    handle_error(listen(server->local_server_soc, 0),
                 " listen to local socket failed");
    event.data.fd = server->local_server_soc;
    event.events = EPOLLIN | EPOLLET;
    handle_error(epoll_ctl(server->epoll, EPOLL_CTL_ADD,
                           server->local_server_soc, &event),
                 " add server socket to epoll failed");
    fprintf(stdout, "[INFO] entering event loop\n");
    sem_post(&semaphore);
    while (true) {
        int nb_of_available_sockets = 0, i = 0;
        nb_of_available_sockets =
            epoll_wait(server->epoll, events, MAX_EVENTS, -1);
        for (i = 0; i != nb_of_available_sockets; ++i) {
            uint32_t e = events[i].events;
            if (e & EPOLLERR || e & EPOLLHUP || !(e & EPOLLIN)) {
                handle_error(-1, "Epoll failed");
            } else if (server->peer_server_soc == events[i].data.fd) {
                accept_new_socket(server->peer_server_soc, server->epoll);
            } else if (server->local_server_soc == events[i].data.fd) {
                handle_local_msg(server);
            } else {
                handle_socket(server, server->epoll, events[i].data.fd);
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

void sync_request(int soc, char* msg, char* buffer) {
    LAST(msg) = 'l';
    pthread_mutex_lock(&transit_mutex);
    handle_error(write(soc, msg, strlen(msg)), "sync write to soc failed");
    read(soc, buffer, BUFFER_SIZE);
    pthread_mutex_unlock(&transit_mutex);
}

void async_request(int soc, char* msg) {
    pthread_mutex_lock(&transit_mutex);
    handle_error(write(soc, msg, strlen(msg)), "async write to soc failed");
    pthread_mutex_unlock(&transit_mutex);
}

void handle_message(struct server_t* server, char* msg, int income_fd) {
    if (LAST(msg) == 'l') {
        LAST(msg) = '\n';
        bool sync = msg[strlen(msg) - 3] == 's';
        msg[strlen(msg) - 2] = '\r';
        sync_request(server->server_soc, msg, server->server_buffer);
        if (sync) {
            write(income_fd, server->server_buffer,
                  strlen(server->server_buffer));
        }
    }
}

void handle_do_join(struct server_t* server, char* buffer) {
    vector_member members = parse_member(buffer);
    int i = 0;
    for (i = 0; i != server->members.size; ++i) {
        bool found = false;
        int j = 0;
        for (j = 0; j != members.size; ++j) {
            if (strcmp(server->members.data[i].name, members.data[j].name) ==
                0) {
                found = true;
                break;
            }
        }
        if (!found) {
            callback_remove(server->members.data[i].name);
        }
    }
    for (i = 0; i != members.size; ++i) {
        bool found = false;
        int j = 0;
        for (j = 0; j != server->members.size; ++j) {
            if (strcmp(server->members.data[j].name, members.data[i].name) ==
                0) {
                found = true;
                break;
            }
        }
        if (!found) {
            callback_add(members.data[i].name);
        }
    }
    free_vector_member(server->members);
    server->members = members;
}

int connect_to_peers(struct server_t* server, char* partial_msg) {
    int index = 0;
    for (index = 0; server->members.data[index].hash_id != server->my_hash_id;
         ++index) {
        ;
    }
    ++index;
    while (server->members.data[index].hash_id != server->my_hash_id) {
        if (!is_backward(server->backwards,
                         server->members.data[index].hash_id)) {
            member peer = server->members.data[index];
            int peer_soc = get_client_socket(peer.ip, peer.port);
            if (peer_soc > 0) {
                int result = handshake(server, peer_soc, partial_msg);
                if (result > 0) {
                    server->forward_soc = result;
                    add_to_listen(server, server->forward_soc);
                    return 0;
                }
            }
        }
        index = (index + 1) % server->members.size;
    }
    return -1;
}

void add_to_listen(struct server_t* server, int soc) {
    struct epoll_event event;
    event.data.fd = soc;
    event.events = EPOLLIN | EPOLLET;
    handle_error(epoll_ctl(server->epoll, EPOLL_CTL_ADD, soc, &event),
                 "add to epoll failed");
}

struct param_t {
    struct server_t* server;
    char* msg;
}

int start_keep_alive(struct server_t* server, char* join_msg) {
    struct param_t* param = malloc(sizeof(struct param_t));
    param->server = server;
    param->msg = join_msg;
    pthread_create(server->keep_alive_thread, nullptr, &keep_alive,
                   (void*)param);
}

void* keep_alive(void* param) {
    struct param_t* p = (struct param_t*)param;
    struct server_t* server = p->server;
    char* join_msg = p->msg;
    sem_init(&server->keep_alive_sem, 0, 0);
    while (server->running) {
        struct timespec ts;
        handle_error(clock_gettime(CLOCK_REALTIME, &ts), "get time failed");
        ts.tv_sec += 20;
        sem_timedwait(&server->keep_alive_sem, &ts);
        if (!server->running) {
            break;
        }
        async_request(server->local_server_soc, join_msg);
    }
}
