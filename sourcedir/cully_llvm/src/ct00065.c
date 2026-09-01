#define ADD(X, Y) (X + Y)


int
testmain()
{
	return ADD(1, 2) - 3;
}

#include <stdio.h>

void main(void)
{
	printf("00065: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
