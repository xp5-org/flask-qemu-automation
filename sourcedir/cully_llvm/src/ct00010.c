int
testmain()
{
	start:
		goto next;
		return 1;
	success:
		return 0;
	next:
	foo:
		goto success;
		return 1;
}

#include <stdio.h>

void main(void)
{
	printf("00010: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
