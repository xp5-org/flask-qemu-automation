double x = 100.0;

int
testmain()
{
	return x < 1;
}

#include <stdio.h>

void main(void)
{
	printf("00123: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
