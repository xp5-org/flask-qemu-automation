int
testmain()
{
	int x, *p;

	if (sizeof(0) < 2)
		return 1;
	if (sizeof 0 < 2)
		return 1;
	if (sizeof(char) < 1)
		return 1;
	if (sizeof(int) - 2 < 0)
		return 1;
	if (sizeof(&x) != sizeof p)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00038: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
