#include <stdio.h>

int testmain() 
{
   printf("Hello\n");
   printf("Hello\n"); /* this is a comment */ printf("Hello\n");
   printf("Hello\n");
   // this is also a comment sayhello();
   printf("Hello\n");

   return 0;
}

// vim: set expandtab ts=4 sw=3 sts=3 tw=80 :

#include <stdio.h>

void main(void)
{
	printf("00131: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
