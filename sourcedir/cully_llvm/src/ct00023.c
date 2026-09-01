int x;

int
testmain()
{
	x = 0;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00023: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
