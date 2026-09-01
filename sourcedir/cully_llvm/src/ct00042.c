int
testmain()
{
	union { int a; int b; } u;
	u.a = 1;
	u.b = 3;
	
	if (u.a != 3 || u.b != 3)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00042: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
