#define X 1
#undef X

#ifdef X
FAIL
#endif

int
testmain()
{
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00071: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
