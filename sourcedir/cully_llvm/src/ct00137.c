#define x(y) #y

int
testmain(void)
{
	char *p;
	p = x(hello)  " is better than bye";

	return (*p == 'h') ? 0 : 1;
}

#include <stdio.h>

void main(void)
{
	printf("00137: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
