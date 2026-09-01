int
testmain()
{
	char *p;
	
	p = "hello";
	return p[0] - 104;
}

#include <stdio.h>

void main(void)
{
	printf("00026: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
