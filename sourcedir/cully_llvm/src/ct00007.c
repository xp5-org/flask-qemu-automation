int
testmain()
{
	int x;
	
	x = 1;
	for(x = 10; x; x = x - 1)
		;
	if(x)
		return 1;
	x = 10;
	for (;x;)
		x = x - 1;
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00007: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
