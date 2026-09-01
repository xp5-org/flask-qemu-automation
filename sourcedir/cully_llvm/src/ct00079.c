#define x(y) ((y) + 1)

int
testmain()
{
	int x;
	int y;
	
	y = 0;
	x = x(y);
	
	if(x != 1)
		return 1;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00079: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
