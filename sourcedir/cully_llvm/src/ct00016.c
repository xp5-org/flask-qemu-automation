int
testmain()
{
	int arr[2];
	int *p;
	
	p = &arr[1];
	*p = 0;
	return arr[1];
}

#include <stdio.h>

void main(void)
{
	printf("00016: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
