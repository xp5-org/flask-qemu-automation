int
testmain()
{
	int x;
	int y;
	x = y = 0;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00011: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
