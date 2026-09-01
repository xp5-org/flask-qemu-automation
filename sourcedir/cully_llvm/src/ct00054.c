enum E {
	x,
	y,
	z,
};

int
testmain()
{
	enum E e;

	if(x != 0)
		return 1;
	if(y != 1)
		return 2;
	if(z != 2)
		return 3;
	
	e = x;
	return e;
}

#include <stdio.h>

void main(void)
{
	printf("00054: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
