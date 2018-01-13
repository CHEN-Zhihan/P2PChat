
#define BUFFER_SIZE 1024

enum state { A, B, C };

struct chat_t {
    char* name;
    enum state current_state;
    int (*setup)(char*, int);
    int (*do_user)(char*);
    int (*do_join)(char*);
    int (*do_list)();
    int (*do_send)(char*);
    int (*do_quit)();
};

struct network_manager_t {
    struct server_manager_t server;
    struct peer_manager_t peer;
    struct socket_handler_t local;
    int local_server;
    vector_peer peers;
    char* join_msg;
    char* partial_handshake_msg;
    pthread_t event_handler;
    struct alive_keeper_t alive_keeper;
    void (*do_send)(char*);
};

switch (event_handler) {
    case local_server: {
        if (do_send) {
            send_to_forward();
        } else {
            write_to_server();
            if (sync) {
                write_back();
            } else {
                update_peers();
            }
            break;
        }
    }
    case server {
        accept_new_socket();
        break;
    }
    case peers {
        if (disconnect) {
            if (forward) {
                reconnect();
            }
        } else {
            send_to_forward();
        }
    }
}
