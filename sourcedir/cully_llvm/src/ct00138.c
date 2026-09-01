#define M(x) x
#define A(a,b) a(b)

int
testmain(void)
{
	char *a = A(M,"hi");

	return (a[1] == 'i') ? 0 : 1;
}

#include <stdio.h>

void main(void)
{
	printf("00138: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
