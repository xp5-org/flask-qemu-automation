#define x f
#define y() f

typedef struct { int f; } S;

int
testmain()
{
	S s;

	s.x = 0;
	return s.y();
}

#include <stdio.h>

void main(void)
{
	printf("00153: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
