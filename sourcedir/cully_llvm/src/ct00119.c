double x = 100;

int
testmain()
{
	return x < 1;
}

#include <stdio.h>

void main(void)
{
	printf("00119: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
