#define X 6 / 2

int
testmain()
{
	return X - 3;
}

#include <stdio.h>

void main(void)
{
	printf("00064: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
