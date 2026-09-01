typedef struct { int x; int y; } s;

s v;

int
testmain()
{
	v.x = 1;
	v.y = 2;
	return 3 - v.x - v.y;
}

#include <stdio.h>

void main(void)
{
	printf("00024: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
