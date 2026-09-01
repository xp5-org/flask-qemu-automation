int
testmain(void)
{
	long i;
	unsigned long u;

	i = 1;
	i = -1;
	i = -1l;
	i = -1u;
	i = -1ll;
	i = (1ll << 32) - 1 & 3;
	i = (long) ((1ll << 32) - 1) < 0;
	i = -1u < 0;

	u = 1;
	u = -1;
	u = -1l;
	u = -1u;
	u = -1ll;
	u = (1ll << 32) - 1 & 3;
	u = (long) ((1ll << 32) - 1) < 0;
	u = -1u < 0;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00134: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
