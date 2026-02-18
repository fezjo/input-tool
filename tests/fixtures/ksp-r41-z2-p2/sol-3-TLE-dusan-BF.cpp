#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main()
{
    ios::sync_with_stdio(0);
    cin.tie(0);
    cout.tie(0);

    int T;
    cin >> T;

    while (T--)
    {
        string sifra;
        cin >> sifra;

        int pos = 0;
        map<char, int> kluc;
        for (auto ch : sifra)
        {
            if (kluc.count(ch) == 0)
            {
                kluc[ch] = pos;
                pos++;
            }
        }

        vector<int> cifry;
        if (kluc.size() == 1)
        {
            cifry.push_back(1);
            for (auto ch : kluc)
                kluc[ch.first] = 1;
        }
        else
            for (int i = 0; i < kluc.size(); i++)
                cifry.push_back(i);

        ll ans = LONG_LONG_MAX;
        do
        {
            int i = 0;
            for (auto ch : kluc)
            {
                kluc[ch.first] = cifry[i];
                i++;
            }
            if (kluc[sifra[0]] != 0)
            {
                ll dlzka_sifry = sifra.length();
                for (ll zaklad = max((ll)2, (ll)kluc.size()); zaklad <= 100; zaklad++)
                {
                    ll nans = 0;
                    for (int i = 0; i < dlzka_sifry; i++)
                    {
                        nans += kluc[sifra[i]] * pow(zaklad, dlzka_sifry - i - 1);
                    }
                    ans = min(ans, nans);
                }
            }
        } while (next_permutation(cifry.begin(), cifry.end()));

        cout << ans << "\n";
    }
}