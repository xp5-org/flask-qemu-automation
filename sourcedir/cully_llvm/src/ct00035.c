int
testmain()
{
	int x;
	
	x = 4;
	if(!x != 0)
		return 1;
	if(!!x != 1)
		return 1;
	if(-x != 0 - 4)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00035: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
