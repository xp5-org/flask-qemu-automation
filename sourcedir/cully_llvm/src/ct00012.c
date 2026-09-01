int
testmain()
{
	return (2 + 2) * 2 - 8;
}

#include <stdio.h>

void main(void)
{
	printf("00012: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
