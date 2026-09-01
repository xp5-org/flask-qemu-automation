int testmain()
{
	int x[] = { 1, 0 };
	return x[1];
}

#include <stdio.h>

void main(void)
{
	printf("00117: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
