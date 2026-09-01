#define BAR 0
#ifdef BAR
	#ifdef FOO
		XXX
		#ifdef FOO
			XXX
		#endif
	#else
		#define FOO
		#ifdef FOO
			int x = BAR;
		#endif
	#endif
#endif

int
testmain()
{
	return BAR;
}

#include <stdio.h>

void main(void)
{
	printf("00063: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
