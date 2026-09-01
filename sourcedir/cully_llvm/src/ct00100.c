int
foo(void)
{
	return 0;
}

int
testmain()
{
	return foo();
}

#include <stdio.h>

void main(void)
{
	printf("00100: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
