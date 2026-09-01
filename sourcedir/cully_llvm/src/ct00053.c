int
testmain()
{
	struct T { int x; } s1;
	s1.x = 1;
	{
		struct T { int y; } s2;
		s2.y = 1;
		if (s1.x - s2.y != 0)
			return 1;
	}
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00053: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
