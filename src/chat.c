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
inline void append_colon(char*);

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
    chat->join_msg = build_join_msg(chat->name, room, port);
    sync_request(chat->local_soc, chat->join_msg, chat->local_buffer);
    if (chat->local_buffer[0] == 'E') {
        return REMOTE_EXCEPTION;
    }
    vector_member members = parse_member(chat->local_buffer);
    chat->server.members = members;
    if (members.size != 1) {
        connect_to_peers(&chat->server);
    }
    start_keep_alive(&chat->server);
    chat->current_state = JOINED_STATE;
    return SUCCESS;
}

char* build_join_msg(const char* name, const char* room, const char* port) {
    char* ip = get_local_IP();
    size_t size = strlen("J:") + strlen(room) + 1 + strlen(name) + 1 +
                  strlen(ip) + 1 + strlen(port) + strlen("::\r\n") + 1;
    char* result = malloc(sizeof(char) * size);
    strcpy(result, "J:");
    result[strlen("J:")] = '\0';
    strcpy(result + strlen(result), room);
    append_colon(result);
    strcpy(result + strlen(result), name);
    append_colon(result);
    strcpy(result + strlen(result), ip);
    append_colon(result);
    strcpy(result + strlen(result), port);
    strcpy(result + strlen(result), "::\r\n");
    result[size - 1] = '\0';
    free(ip);
    return result;
}

inline void append_colon(char* s) {
    int size = strlen(s);
    s[size] = ':';
    s[size + 1] = '\0';
}
