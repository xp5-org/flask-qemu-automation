int
testmain()
{
	int x;
	void *foo;
	void **bar;
	
	x = 0;
	
	foo = (void*)&x;
	bar = &foo;
	
	return **(int**)bar;
}

#include <stdio.h>

void main(void)
{
	printf("00103: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
