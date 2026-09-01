#define A 3
#define FOO(X,Y,Z) X + Y + Z
#define SEMI ;

int
testmain()
{
	if(FOO(1, 2, A) != 6)
		return 1 SEMI
	return FOO(0,0,0);
}

#include <stdio.h>

void main(void)
{
	printf("00066: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
