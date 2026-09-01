struct S1 { int x; };
struct S2 { struct S1 s1; };

int
testmain()
{
	struct S2 s2;
	s2.s1.x = 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00106: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
