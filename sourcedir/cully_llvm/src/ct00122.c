#define F(a, b) a
int
testmain()
{
	return F(, 1) 0;
}

#include <stdio.h>

void main(void)
{
	printf("00122: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
