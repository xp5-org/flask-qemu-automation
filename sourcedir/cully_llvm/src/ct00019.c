int
testmain()
{
	struct S { struct S *p; int x; } s;
	
	s.x = 0;
	s.p = &s;
	return s.p->p->p->p->p->x;
}

#include <stdio.h>

void main(void)
{
	printf("00019: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
