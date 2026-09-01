int a[3] = {0, 1, 2};

int
testmain()
{
	if (a[0] != 0)
		return 1;
	if (a[1] != 1)
		return 2;
	if (a[2] != 2)
		return 3;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00090: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
