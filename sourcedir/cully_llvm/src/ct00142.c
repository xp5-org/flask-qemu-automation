#if defined(FOO)
int a;
#elif !defined(FOO) && defined(BAR)
int b;
#elif !defined(FOO) && !defined(BAR)
int c;
#else
int d;
#endif

int
testmain(void)
{
	return c;
}

#include <stdio.h>

void main(void)
{
	printf("00142: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
