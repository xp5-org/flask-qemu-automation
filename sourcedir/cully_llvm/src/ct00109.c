int
testmain()
{
	int x = 0;
	int y = 1;
	if(x ? 1 : 0)
		return 1;
	if(y ? 0 : 1)
		return 2;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00109: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
