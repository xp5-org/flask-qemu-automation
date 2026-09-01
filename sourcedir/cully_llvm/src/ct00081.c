int
testmain()
{
	long long x;
	
	x = 0;
	x = x + 1;
	if (x != 1)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00081: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
