int x;
int x = 3;
int x;

int testmain();

void *
foo()
{
	return &testmain;
}

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
	printf("00095: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
