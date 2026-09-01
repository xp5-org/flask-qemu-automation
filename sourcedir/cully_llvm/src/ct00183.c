#include <stdio.h>

int testmain()
{
   int Count;

   for (Count = 0; Count < 10; Count++)
   {
      printf("%d\n", (Count < 5) ? (Count*Count) : (Count * 3));
   }

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00183: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
