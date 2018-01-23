#include "message.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char* build_info_msg(char*, char*, char*, int);

char* build_list_msg() { return "L::\r\n"; }

char* build_info_msg(char* room, char* name, char* ip, int port) {
    char port_str[10];
    snprintf(port_str, sizeof(port_str), "%d", port);
    size_t size = strlen(room) + 1 + strlen(name) + 1 + strlen(ip) + 1 +
                  strlen(port_str) + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "%s:%s:%s:%s", room, name, ip,
             port_str);
    return result;
}

char* build_join_msg(char* room, char* name, char* ip, int port) {
    char* partial_msg = build_info_msg(room, name, ip, port);
    size_t size = strlen("J:") + strlen(partial_msg) + strlen("::\r\n") + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "J:%s::\r\n", partial_msg);
    free(partial_msg);
    return result;
}

char* build_partial_handshake_msg(char* room, char* name, char* ip, int port) {
    char* partial_msg = build_info_msg(room, name, ip, port);
    size_t size = strlen("P:") + strlen(partial_msg) + 2;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "P:%s:", partial_msg);
    free(partial_msg);
    return result;
}

char* build_handshake_msg(char* partial, int msgid) {
    char msg[10];
    snprintf(msg, 10, "%d", msgid);
    size_t size = strlen(partial) + strlen(msg) + strlen("::\r\n") + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, sizeof(*result) * size, "%s%s::\r\n", partial, msg);
    return result;
}

void free_message(struct message_t m) {
    free(m.content);
    free(m.name);
    free(m.room);
}

char* build_partial_send_msg(char* room, unsigned long hash_id, char* name) {
    char id[100];
    snprintf(id, 100, "%lu", hash_id);
    size_t size = 2 + strlen(room) + 1 + strlen(id) + 1 + strlen(name) + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, size, "T:%s:%s:%s", room, id, name);
    return result;
}

char* build_send_msg(char* partial, int msgid, char* msg) {
    char msgid_str[10];
    snprintf(msgid_str, 10, "%d", msgid);
    char msg_len[10];
    snprintf(msg_len, 10, "%lu", strlen(msg));
    size_t size = strlen(partial) + 1 + strlen(msgid_str) + 1 +
                  strlen(msg_len) + strlen("::\r\n") + 1;
    char* result = malloc(sizeof(*result) * size);
    snprintf(result, size, "%s:%s:%s:%s::\r\n", partial, msgid_str, msg_len,
             msg);
    return result;
}
