int x, x = 3, x;

int
testmain()
{
	if (x != 3)
		return 0;

	x = 0;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00096: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
