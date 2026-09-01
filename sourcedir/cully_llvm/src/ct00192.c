#include <stdio.h>

int testmain()
{
   int Count = 0;

   for (;;)
   {
      Count++;
      printf("%d\n", Count);
      if (Count >= 10)
         break;
   }

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00192: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
