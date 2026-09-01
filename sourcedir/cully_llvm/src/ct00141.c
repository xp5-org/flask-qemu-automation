#define CAT(x,y) x ## y
#define XCAT(x,y) CAT(x,y)
#define FOO foo
#define BAR bar

int
testmain(void)
{
	int foo, bar, foobar;

	CAT(foo,bar) = foo + bar;
	XCAT(FOO,BAR) = foo + bar;
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00141: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
