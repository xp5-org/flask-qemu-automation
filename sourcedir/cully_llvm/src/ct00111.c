int
testmain()
{
	short s = 1;
	long l = 1;

	s -= l;
	return s;
}

#include <stdio.h>

void main(void)
{
	printf("00111: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
