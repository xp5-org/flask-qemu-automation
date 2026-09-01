int
foo(int a, int b)
{
	return 2 + a - b;
}

int
testmain()
{
	return foo(1, 3);
}

#include <stdio.h>

void main(void)
{
	printf("00021: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
