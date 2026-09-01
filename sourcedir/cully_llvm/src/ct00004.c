int
testmain()
{
	int x;
	int *p;
	
	x = 4;
	p = &x;
	*p = 0;

	return *p;
}

#include <stdio.h>

void main(void)
{
	printf("00004: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
