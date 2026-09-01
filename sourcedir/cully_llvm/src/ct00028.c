int
testmain()
{
	int x;
	
	x = 1;
	x = x & 3;
	return x - 1;
}

#include <stdio.h>

void main(void)
{
	printf("00028: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
