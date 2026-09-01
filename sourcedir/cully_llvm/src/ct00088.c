int (*fptr)() = 0;


int
testmain()
{
	if (fptr)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00088: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
