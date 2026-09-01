int
testmain()
{
	int x;
	int *p;
	
	x = 1;
	p = &x;
	p[0] = 0;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00014: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
