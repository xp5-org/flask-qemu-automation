struct S
{
	int	(*fptr)();
};

int
foo()
{
	return 0;
}

int
testmain()
{
	struct S v;
	
	v.fptr = foo;
	return v.fptr();
}

#include <stdio.h>

void main(void)
{
	printf("00087: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
