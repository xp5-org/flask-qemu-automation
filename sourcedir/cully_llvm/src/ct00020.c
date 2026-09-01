int
testmain()
{
	int x, *p, **pp;
	
	x = 0;
	p = &x;
	pp = &p;
	return **pp;
}

#include <stdio.h>

void main(void)
{
	printf("00020: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
