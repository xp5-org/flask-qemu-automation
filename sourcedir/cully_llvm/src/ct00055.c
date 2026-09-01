enum E {
	x,
	y = 2,
	z,
};

int
testmain()
{
	enum E e;

	if(x != 0)
		return 1;
	if(y != 2)
		return 2;
	if(z != 3)
		return 3;
	
	e = x;
	return e;
}

#include <stdio.h>

void main(void)
{
	printf("00055: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
