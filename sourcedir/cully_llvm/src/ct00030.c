int
f()
{
	return 100;
}

int
testmain()
{
	if (f() > 1000)
		return 1;
	if (f() >= 1000)
		return 1;
	if (1000 < f())
		return 1;
	if (1000 <= f())
		return 1;
	if (1000 == f())
		return 1;
	if (100 != f())
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00030: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
