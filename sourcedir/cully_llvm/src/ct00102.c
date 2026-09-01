int
testmain()
{
	int x;
	
	x = 1;
	if ((x << 1) != 2)
		return 1;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00102: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
