struct { int a; int b; int c; } s = {1, 2, 3};

int
testmain()
{
	if (s.a != 1)
		return 1;
	if (s.b != 2)
		return 2;
	if (s.c != 3)
		return 3;

	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00047: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
