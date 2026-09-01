int
testmain()
{
	struct { int x; int y; } s;
	
	s.x = 3;
	s.y = 5;
	return s.y - s.x - 2; 
}

#include <stdio.h>

void main(void)
{
	printf("00017: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
