typedef int myint;
myint x = (myint)1;

int
testmain(void)
{
	return x-1;
}

#include <stdio.h>

void main(void)
{
	printf("00107: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
