#include "chat.h"
#include <string.h>
int print(const char* s) {
    fprintf(stdout, "%s\n", s);
    return strlen(s);
}
