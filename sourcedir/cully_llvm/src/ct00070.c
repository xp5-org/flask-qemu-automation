#ifndef DEF
int x = 0;
#endif

#define DEF

#ifndef DEF
X
#endif

int
testmain()
{
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00070: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
