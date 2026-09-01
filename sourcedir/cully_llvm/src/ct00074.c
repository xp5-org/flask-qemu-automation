#if defined X
X
#endif

#if defined(X)
X
#endif

#if X
X
#endif

#define X 0

#if X
X
#endif

#if defined(X)
int x = 0;
#endif

#undef X
#define X 1

#if X
int
testmain()
{
	return 0;
}
#endif

#include <stdio.h>

void main(void)
{
	printf("00074: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
