int
testmain()
{
	int arr[2];
	int *p;
	
	p = &arr[0];
	p += 1;
	*p = 123;
	
	if(arr[1] != 123)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00072: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
