int
testmain()
{
	int x;
	
	x = 1;
	x = x | 4;
	return x - 5;
}

#include <stdio.h>

void main(void)
{
	printf("00027: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
