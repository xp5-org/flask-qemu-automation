int
testmain()
{
	void *p;
	int x;
	
	x = 2;
	p = &x;
	
	if(*((int*)p) != 2)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00039: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
