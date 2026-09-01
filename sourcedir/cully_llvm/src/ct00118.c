int
testmain()
{
	struct { int x; } s = { 0 };
	return s.x;
}

#include <stdio.h>

void main(void)
{
	printf("00118: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
