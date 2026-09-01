#ifdef FOO
	XXX
#ifdef BAR
	XXX
#endif
	XXX
#endif

#define FOO 1

#ifdef FOO

#ifdef FOO
int x = 0;
#endif

int
testmain()
{
	return x;
}
#endif

#include <stdio.h>

void main(void)
{
	printf("00062: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
