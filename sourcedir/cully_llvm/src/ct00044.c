struct T;

struct T {
	int x;
};

int
testmain()
{
	struct T v;
	{ struct T { int z; }; }
	v.x = 2;
	if(v.x != 2)
		return 1;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00044: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
