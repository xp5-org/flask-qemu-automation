int
testmain()
{
	int x;

	x = 50;
	while (x)
		x = x - 1;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00006: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
