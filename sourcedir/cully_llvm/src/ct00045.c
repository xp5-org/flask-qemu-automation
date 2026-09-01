int x = 5;
long y = 6;
int *p = &x;

int
testmain()
{
	if (x != 5) 
		return 1;
	if (y != 6)
		return 2;
	if (*p != 5)
		return 3;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00045: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
