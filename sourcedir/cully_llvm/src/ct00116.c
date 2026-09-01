int
f(int f)
{
	return f;
}

int
testmain()
{
	return f(0);
}

#include <stdio.h>

void main(void)
{
	printf("00116: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
