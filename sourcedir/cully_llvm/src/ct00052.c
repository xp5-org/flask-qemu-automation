int
testmain()
{
	struct T { int x; };
	{
		struct T s;
		s.x = 0;
		return s.x;
	}
}

#include <stdio.h>

void main(void)
{
	printf("00052: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
