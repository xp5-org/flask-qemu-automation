extern int x;

int testmain()
{
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00094: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
