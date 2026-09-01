int a[] = {1, 2, 3, 4};

int
testmain()
{
	if (sizeof(a) != 4*sizeof(int))
		return 1;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00093: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
