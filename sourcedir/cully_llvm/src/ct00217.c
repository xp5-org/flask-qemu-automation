int printf(const char *, ...);
char t[] = "012345678";

int testmain(void)
{
    char *data = t;
    unsigned long long r = 4;
    unsigned a = 5;
    unsigned long long b = 12;

    *(unsigned*)(data + r) += a - b;

    printf("data = \"%s\"\n", data);
    return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00217: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
