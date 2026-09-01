struct foo {
	int i, j, k;
	char *p;
	float v;
};

int
f1(struct foo f, struct foo *p, int n, ...)
{
	if (f.i != p->i)
		return 0;
	return p->j + n;
}

int
testmain(void)
{
	struct foo f;

	f.i = f.j = 1;
	f1(f, &f, 2);
	f1(f, &f, 2, 1, f, &f);

	return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00140: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
