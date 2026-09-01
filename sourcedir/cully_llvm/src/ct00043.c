struct s {
    int x;
    struct {
        int y;
        int z;
    } nest;
};

int
testmain() {
    struct s v;
    v.x = 1;
    v.nest.y = 2;
    v.nest.z = 3;
    if (v.x + v.nest.y + v.nest.z != 6)
        return 1;
    return 0;
}

#include <stdio.h>

void main(void)
{
	printf("00043: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
