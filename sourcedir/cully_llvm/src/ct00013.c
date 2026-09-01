int
testmain()
{
	int x;
	int *p;
	
	x = 0;
	p = &x;
	return p[0];
}

#include <stdio.h>

void main(void)
{
	printf("00013: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
