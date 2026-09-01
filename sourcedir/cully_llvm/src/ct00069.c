#if 0
X
#elif 0
X
#elif 1
int x = 0;
#endif

int
testmain()
{
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00069: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
