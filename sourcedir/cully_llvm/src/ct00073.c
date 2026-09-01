int
testmain()
{
	int arr[2];
	int *p;
	
	p = &arr[1];
	p -= 1;
	*p = 123;
	
	if(arr[0] != 123)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00073: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
