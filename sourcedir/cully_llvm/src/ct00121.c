int f(int a), g(int a), a;


int
testmain()
{
	return f(1) - g(1);
}

int
f(int a)
{
	return a;
}

int
g(int a)
{
	return a;
}

#include <stdio.h>

void main(void)
{
	printf("00121: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
