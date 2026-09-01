
int
testmain(void)
{
	sizeof((int) 1);
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00155: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
