#include "network_manager.h"
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include "chat_wrapper.h"
#include "parser.h"
#include "peer_manager.h"

void setup_event_loop(struct network_manager_t*);
void* event_loop(void*);
void* keep_alive_loop(void*);
void add_to_epoll(int, int);
void update_member_list(struct network_manager_t*);
int handle_local_message(struct network_manager_t*);

int setup_network(struct network_manager_t* manager, char* addr, char* local_ip,
                  int server_port, int local_port) {
    manager->server.fd = get_client_socket(addr, server_port);
    setup_peer_server(&manager->peer, local_ip, local_port);
    local_port = (local_port + 1) % 65535;
    manager->local_server = get_server_socket_try_port(local_ip, &local_port);
    pthread_create(&manager->event_handler, nullptr, &event_loop,
                   (void*)manager);
    return get_client_socket(local_ip, local_port);
}

void* event_loop(void* m) {
    struct network_manager_t* manager = (struct network_manager_t*)m;
    manager->local.fd = accept(manager->local_server, nullptr, nullptr);
    if (manager->local.fd < 0) {
        fprintf(stderr, "[ERROR] accept returns negative ones");
        fprintf(stderr, "%d\t%s\n", errno == EINVAL, strerror(errno));
        exit(EXIT_FAILURE);
    }
    int epoll = epoll_create1(0);
    add_to_epoll(epoll, manager->local.fd);
    add_to_epoll(epoll, manager->peer.server);
    static const int MAX_EVENTS = 10;
    struct epoll_event events[MAX_EVENTS];
    while (true) {
        int available_number = 0, i = 0;
        available_number = epoll_wait(epoll, events, MAX_EVENTS, -1);
        for (i = 0; i != available_number; ++i) {
            uint32_t e = events[i].events;
            if (e & EPOLLERR || e & EPOLLHUP || !(e & EPOLLIN)) {
                handle_error(-1, "epoll wait failed");
            }
            int fd = events[i].data.fd;
            if (fd == manager->local.fd) {
                int result = handle_local_message(manager);
                if (result < 0) {
                    break;
                } else if (result > 0) {
                    add_to_epoll(epoll, result);
                }
            } else if (fd == manager->peer.server) {
                int new_peer_fd = handle_new_peer(&manager->peer, manager);
                if (new_peer_fd > 0) {
                    add_to_epoll(epoll, new_peer_fd);
                }
            } else {
                int result = handle_peer_message(&manager->peer, manager, fd);
                if (result != 0) {
                    handle_error(epoll_ctl(epoll, EPOLL_CTL_DEL, fd, nullptr),
                                 "remove from epoll failed");
                    if (result > 0) {
                        add_to_epoll(epoll, result);
                    }
                }
            }
        }
    }
    close_connected_peers(&manager->peer);
    close(epoll);
    close(manager->local.fd);
    return nullptr;
}

void add_to_epoll(int epoll, int fd) {
    struct epoll_event event;
    make_non_block(fd);
    event.data.fd = fd;
    event.events = EPOLLIN | EPOLLET;
    handle_error(epoll_ctl(epoll, EPOLL_CTL_ADD, fd, &event),
                 "add to epoll failed");
}

int handle_local_message(struct network_manager_t* manager) {
    read(manager->local.fd, manager->local.buffer, BUFFER_SIZE);
    char request_flag = manager->local.buffer[0];
    int result = 0;
    if (request_flag == 'Q') {
        return -1;
    }
    if (request_flag == 'L' || request_flag == 'J' || request_flag == 'A') {
        if (request_flag == 'A') {
            manager->local.buffer[0] = 'J';
        }
        write(manager->server.fd, manager->local.buffer,
              strlen(manager->local.buffer));
        read(manager->server.fd, manager->server.buffer, BUFFER_SIZE);
        if (request_flag == 'L' || request_flag == 'J') {
            write(manager->local.fd, manager->server.buffer,
                  strlen(manager->server.buffer));
        }
        if (request_flag == 'A' || request_flag == 'J') {
            update_member_list(manager);
        }
        if (request_flag == 'J') {
            result = connect_to_peer(&manager->peer, manager->peers);
        }
    } else if (request_flag == 'T') {
        send_msg(&manager->peer, manager->local.buffer);
    }
    return result;
}

void setup_keep_alive(struct network_manager_t* manager, char* join_msg,
                      int soc) {
    manager->alive_keeper.join_msg = join_msg;
    manager->alive_keeper.join_msg[0] = 'A';
    manager->alive_keeper.local_client = soc;
    sem_init(&manager->alive_keeper.timeout, 0, 0);
    pthread_create(&manager->alive_keeper.monitor, nullptr, &keep_alive_loop,
                   (void*)&manager->alive_keeper);
}

void* keep_alive_loop(void* k) {
    struct alive_keeper_t* alive_keeper = (struct alive_keeper_t*)k;
    while (alive_keeper->running) {
        struct timespec ts;
        handle_error(clock_gettime(CLOCK_REALTIME, &ts),
                     "clock_gettime failed");
        ts.tv_sec += 20;
        sem_timedwait(&alive_keeper->timeout, &ts);
        if (!alive_keeper->running) {
            break;
        }
        async_request(alive_keeper->local_client, alive_keeper->join_msg);
    }
    sem_destroy(&alive_keeper->timeout);
    return nullptr;
}

void compare_and_callback(vector_peer_t p1, vector_peer_t p2,
                          void (*callback)(char*)) {
    int i = 0;
    for (i = 0; i != p1.size; ++i) {
        int j = 0;
        bool found = false;
        for (j = 0; j != p2.size; ++j) {
            if (p1.data[i].hash_id == p2.data[j].hash_id) {
                found = true;
                break;
            }
        }
        if (!found) {
            callback(p1.data[i].name);
        }
    }
}

void update_member_list(struct network_manager_t* manager) {
    vector_peer_t peers = parse_peers(manager->server.buffer);
    compare_and_callback(manager->peers, peers, &callback_remove);
    compare_and_callback(peers, manager->peers, &callback_add);
    if (manager->peers.size != 0) {
        free_vector_peer(manager->peers);
    }
    manager->peers = peers;
    sort_peers(&manager->peers, 0, manager->peers.size);
}

void check_and_update(struct network_manager_t* manager, long hash_id) {
    if (!is_member(manager->peers, hash_id)) {
        char* join_msg = strdup(manager->alive_keeper.join_msg);
        join_msg[0] = 'J';
        write(manager->server.fd, join_msg, strlen(manager->local.buffer));
        read(manager->server.fd, manager->server.buffer, BUFFER_SIZE);
        update_member_list(manager);
        free(join_msg);
    }
}
