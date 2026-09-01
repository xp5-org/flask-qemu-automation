int
testmain()
{
	return "abc" == (void *)0;
}

#include <stdio.h>

void main(void)
{
	printf("00112: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
