int
f1(char *p)
{
	return *p+1;
}

int
testmain()
{
	char s = 1;
	int v[1000];
	int f1(char *);

	if (f1(&s) != 2)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00078: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
