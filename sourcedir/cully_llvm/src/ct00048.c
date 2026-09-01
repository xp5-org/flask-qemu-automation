struct S {int a; int b;};
struct S s = { .b = 2, .a = 1};

int
testmain()
{
	if(s.a != 1)
		return 1;
	if(s.b != 2)
		return 2;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00048: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
