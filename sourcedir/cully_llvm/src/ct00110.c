extern int x;
int x;

int
testmain()
{
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00110: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
