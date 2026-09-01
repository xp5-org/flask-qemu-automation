int
testmain()
{
	char a[16], b[16];
	
	if(sizeof(a) != sizeof(b))
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00057: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
