int
testmain()
{
	if(0 ? 1 : 0)
		return 1;
	if(1 ? 0 : 1)
		return 2;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00076: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
