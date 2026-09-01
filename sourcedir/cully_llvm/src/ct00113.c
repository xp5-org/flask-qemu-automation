int
testmain()
{
	int a = 0;
	float f = a + 1;

	return f == a;
}

#include <stdio.h>

void main(void)
{
	printf("00113: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
