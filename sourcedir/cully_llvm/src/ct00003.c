int
testmain()
{
	int x;
	
	x = 4;
	return x - 4;
}

#include <stdio.h>

void main(void)
{
	printf("00003: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
