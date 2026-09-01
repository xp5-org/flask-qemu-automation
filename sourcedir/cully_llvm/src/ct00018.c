int
testmain()
{

	struct S { int x; int y; } s;
	struct S *p;

	p = &s;	
	s.x = 1;
	p->y = 2;
	return p->y + p->x - 3; 
}

#include <stdio.h>

void main(void)
{
	printf("00018: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
