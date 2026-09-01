int arr[][3][5] = {
	{
		{ 0, 0, 3, 5 },
		{ 1, [3] = 6, 7 },
	},
	{
		{ 1, 2 },
		{ [4] = 7, },
	},
};

int
testmain(void)
{
	return !(arr[0][1][4] == arr[1][1][4]);
}

#include <stdio.h>

void main(void)
{
	printf("00151: %s\n", testmain() == 0 ? "PASS" : "FAIL");
}
