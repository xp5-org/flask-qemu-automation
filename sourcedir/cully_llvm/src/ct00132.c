#include <stdio.h>

int testmain() 
{
   printf("Hello world\n");

   int Count;
   for (Count = -5; Count <= 5; Count++)
      printf("Count = %d\n", Count);

   printf("String 'hello', 'there' is '%s', '%s'\n", "hello", "there");
   printf("Character 'A' is '%c'\n", 65);
   printf("Character 'a' is '%c'\n", 'a');

   return 0;
}

// vim: set expandtab ts=4 sw=3 sts=3 tw=80 :

#include <stdio.h>

void main(void)
{
	printf("00132: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
