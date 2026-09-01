int
testmain()
{
	int x;

	x = 50;
	do 
		x = x - 1;
	while(x);
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00008: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
