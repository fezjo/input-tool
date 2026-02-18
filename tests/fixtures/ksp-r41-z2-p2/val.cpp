#include <bits/stdc++.h>
#include "../../testlib.h"
using namespace std;
using ll = long long;

/*
| Sada            |    1 |    2 |      3 |      4 |           5, 6 |   7, 8 |
| :-------------- | ---: | ---: | -----: | -----: | -------------: | -----: |
| $1 \leq t \leq$ | $10$ | $10$ | $10^3$ | $10^4$ | $3 \cdot 10^4$ | $10^5$ |
| $1 \leq l \leq$ |  $3$ |  $4$ |    $5$ |    $6$ |           $10$ |   $19$ |
*/
// zeroth value is for samples
vector<int> maxT = {3, 10, 10, 1000, (int)1e4, (int)3e4, (int)3e4, (int)1e5, (int)1e5};
vector<int> maxL = {4, 4, 5, 6, 10, 10, 19, 19, 19};

int main(int argc, char *argv[]) {
    ios::sync_with_stdio(0);
    cin.tie(0);
    cout.tie(0);
    registerValidation();

    int batch = atoi(argv[1]);

    int T;
    T = inf.readInt(1, maxT[batch], "T");
    inf.readEoln();

    for (int t = 0; t < T; t++)
    {
        string sifra;
        sifra = inf.readString("[a-zA-Z0-9]*");
        ensuref(sifra.length() <= maxL[batch], "sifra ma viac ako %d znakov", maxL[batch]);
        set<char> unique(sifra.begin(), sifra.end());
        ensuref(unique.size() <= 10, "sifra ma viac ako 10 roznych znakov");
    }

    inf.readEof();
}
