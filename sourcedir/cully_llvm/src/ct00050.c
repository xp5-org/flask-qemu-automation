struct S1 {
	int a;
	int b;
};

struct S2 {
	int a;
	int b;
	union {
		int c;
		int d;
	};
	struct S1 s;
};

struct S2 v = {1, 2, 3, {4, 5}};

int
testmain()
{
	if(v.a != 1)
		return 1;
	if(v.b != 2)
		return 2;
	if(v.c != 3 || v.d != 3)
		return 3;
	if(v.s.a != 4)
		return 4;
	if(v.s.b != 5)
		return 5;
	
	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00050: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
