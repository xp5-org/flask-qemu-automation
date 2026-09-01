int a[] = {5, [2] = 2, 3};

int
testmain()
{
	if (sizeof(a) != 4*sizeof(int))
		return 1;
		
	if (a[0] != 5)
		return 2;
	if (a[1] != 0)
		return 3;
	if (a[2] != 2)
		return 4;
	if (a[3] != 3)
		return 5;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00092: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
