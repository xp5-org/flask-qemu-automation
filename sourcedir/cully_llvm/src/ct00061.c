#define FOO 0

int testmain()
{
	return FOO;
}

#include <stdio.h>

void main(void)
{
	printf("00061: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
