#include "chat.h"
#include <string.h>
int doUser(const char* s) {
    fprintf(stdout, "%s\n", s);
    return strlen(s);
}
