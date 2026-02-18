#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
    ios::sync_with_stdio(0);
    cin.tie(0);
    cout.tie(0);

    int T;
    cin >> T;

    while (T--) {
        string sifra;
        cin >> sifra;

        int kolkate = 0;

        map<char, int> kluc;
        for (auto ch : sifra) {
            if (kluc.count(ch) == 0) {
                if (kolkate == 0)
                    kluc[ch] = 1;
                else if (kolkate == 1)
                    kluc[ch] = 0;
                else
                    kluc[ch] = kolkate;
                kolkate++;
            }
        }

        ll dlzka_sifry = sifra.length();
        ll odpoved = LONG_LONG_MAX;
        for (ll zaklad = 1; zaklad <= 30; zaklad++) {
            ll nans = 0;
            for (int i = 0; i < dlzka_sifry; i++) {
                nans += kluc[sifra[i]] * pow(zaklad, dlzka_sifry - i - 1);
            }
            if (zaklad >= max(2, (int)kluc.size()))
                odpoved = min(odpoved, nans);
        }
        cout << odpoved << "\n";
    }
}