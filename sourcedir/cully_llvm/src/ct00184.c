#include <stdio.h>

int testmain()
{
   char a;
   short b;

   printf("%d %d\n", sizeof(char), sizeof(a));
   printf("%d %d\n", sizeof(short), sizeof(b));

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00184: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
