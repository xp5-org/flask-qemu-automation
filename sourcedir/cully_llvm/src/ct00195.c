#include <stdio.h>

struct point
{
   double x;
   double y;
};

struct point point_array[100];

int testmain()
{
   int my_point = 10;

   point_array[my_point].x = 12.34;
   point_array[my_point].y = 56.78;

   printf("%f, %f\n", point_array[my_point].x, point_array[my_point].y);

   return 0;
}

/* vim: set expandtab ts=4 sw=3 sts=3 tw=80 :*/

#include <stdio.h>

void main(void)
{
	printf("00195: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
