int
testmain()
{
	return 3-3;
}

#include <stdio.h>

void main(void)
{
	printf("00002: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
