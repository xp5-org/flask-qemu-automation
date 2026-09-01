int
zero()
{
	return 0;
}

struct S
{
	int (*zerofunc)();
} s = { &zero };

struct S *
anon()
{
	return &s;
}

typedef struct S * (*fty)();

fty
go()
{
	return &anon;
}

int
testmain()
{
	return go()()->zerofunc();
}

#include <stdio.h>

void main(void)
{
	printf("00089: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
