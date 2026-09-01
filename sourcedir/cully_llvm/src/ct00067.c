#if 1
int x = 0;
#endif

#if 0
int x = 1;
#if 1
 X
#endif
#ifndef AAA
 X
#endif
#endif

int testmain()
{
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00067: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
