#define NULL ((void*)0)
#define NULL ((void*)0)

#define FOO(X, Y) (X + Y + Z)
#define FOO(X, Y) (X + Y + Z)

#define BAR(X, Y, ...) (X + Y + Z)
#define BAR(X, Y, ...) (X + Y + Z)

int
testmain()
{
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00097: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
