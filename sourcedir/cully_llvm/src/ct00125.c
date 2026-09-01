#include <stdio.h>

int
testmain(void)
{
	printf("hello world\n");
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00125: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
