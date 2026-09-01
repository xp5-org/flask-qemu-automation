typedef int x;

int
testmain()
{
	x v;
	v = 0;
	return v;
}

#include <stdio.h>

void main(void)
{
	printf("00022: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
