#undef  line
#define line 1000

#line line
#if 1000 != __LINE__
	#error "  # line line" not work as expected
#endif

int
testmain()
{
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00152: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
