int
testmain()
{
	int x;
	
	x = 1;
	x = x ^ 3;
	return x - 2;
}

#include <stdio.h>

void main(void)
{
	printf("00029: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
