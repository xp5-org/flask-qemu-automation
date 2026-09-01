#if 0
X
#elif 1
int x = 0;
#else
X
#endif

int
testmain()
{
	return x;
}

#include <stdio.h>

void main(void)
{
	printf("00068: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
