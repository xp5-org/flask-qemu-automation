int
testmain()
{
	int x;
	int *p;
	int **pp;

	x = 0;
	p = &x;
	pp = &p;

	if(*p)
		return 1;
	if(**pp)
		return 1;
	else
		**pp = 1;

	if(x)
		return 0;
	else
		return 1;
}

#include <stdio.h>

void main(void)
{
	printf("00005: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
