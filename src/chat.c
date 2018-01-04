#include "chat.h"
#include <string.h>

int do_user(const char* s) {
    fprintf(stdout, "register as user %s\n", s);
    return SUCCESS;
}
