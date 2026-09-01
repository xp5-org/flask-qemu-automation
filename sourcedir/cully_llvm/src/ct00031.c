int
zero()
{
	return 0;
}

int
one()
{
	return 1;
}

int
testmain()
{
	int x;
	int y;
	
	x = zero();
	y = ++x;
	if (x != 1)
		return 1;
	if (y != 1)
		return 1;
	
	x = one();	
	y = --x;
	if (x != 0)
		return 1;
	if (y != 0)
		return 1;
	
	x = zero();
	y = x++;
	if (x != 1)
		return 1;
	if (y != 0)
		return 1;
	
	x = one();
	y = x--;
	if (x != 0)
		return 1;
	if (y != 1)
		return 1;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00031: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
