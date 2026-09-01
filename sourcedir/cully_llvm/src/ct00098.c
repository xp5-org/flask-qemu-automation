int
testmain()
{
	return L'\0';
}

#include <stdio.h>

void main(void)
{
	printf("00098: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
