#include "chat.h"
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "local_server.h"
#include "network.h"
#include "parser.h"

char* build_join_msg(const char*, const char*, const char*);
void process_join(struct chat_t*);
void setup_keep_alive(struct chat_t*);
char* concat_info(char* room, char* name, char* ip, char* port);

void setup(struct chat_t* chat, char* serv_addr, int serv_port, int port) {
    chat->current_state = START_STATE;
    chat->port = port;
    chat->local_soc = setup_local_server(&chat->server, port);
    fprintf(stdout, "[INFO] Complete setting up local server\n");
    connect_to_server(&chat->server, serv_addr, serv_port);
}

int do_user(struct chat_t* chat, const char* s) {
    if (chat->current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    chat->name = strdup(s);
    chat->current_state = NAMED_STATE;
    return SUCCESS;
}

vector_str do_list(struct chat_t* chat) {
    sync_request(chat->local_soc, "L::\r\n", chat->local_buffer);
    vector_str result = parse_do_list(chat->local_buffer);
    return result;
}

int do_join(struct chat_t* chat, const char* room) {
    if (chat->current_state == JOINED_STATE) {
        return JOINED_EXCEPTION;
    }
    if (chat->current_state == START_STATE) {
        return UNNAMED_EXCEPTION;
    }
    char port[10];
    sprintf(port, "%d", chat->port);
    char* ip = get_local_IP();
    chat->join_msg = build_join_msg(room, chat->name, ip, port);
    chat->server.my_hash_id = hash(chat->name, ip, port);
    sync_request(chat->local_soc, chat->join_msg, chat->local_buffer);
    if (chat->local_buffer[0] == 'E') {
        return REMOTE_EXCEPTION;
    }
    chat->server.members = parse_member(chat->local_buffer);
    sort_members(&chat->server.members, 0, chat->server.members.data);
    chat->partial_handshake_msg =
        build_partial_handshake_msg(room, chat->name, ip, port);
    if (chat->server.members.size != 1) {
        connect_to_peers(&chat->server, chat->partial_handshake_msg);
    }
    start_keep_alive(&chat->server, chat->local_soc, chat->join_msg);
    chat->current_state = JOINED_STATE;
    free(ip);
    return SUCCESS;
}

char* build_join_msg(char* room, char* name, char* ip, char* port) {
    char* partial_msg = concat_info(room, name, ip, port);
    size_t size = strlen("J:") + strlen(partial_msg) + strlen("::\r\n") + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "J:%s::\r\n", partial_msg);
    free(partial_msg);
    return result;
}

char* build_partial_handshake_msg(char* room, char* name, char* ip,
                                  char* port) {
    char* partial_msg = concat_info(room, name, ip, port);
    size_t size = strlen("P:") + strlen(partial_msg) + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "P:%s", partial_msg);
    free(partial_msg);
    return result;
}

char* concat_info(char* room, char* name, char* ip, char* port) {
    size_t size =
        strlen(room) + 1 + strlen(name) + 1 + strlen(ip) + 1 + strlen(port) + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "%s:%s:%s:%s", room, name, ip,
             port);
    return result;
}
