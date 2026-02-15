#include <iostream>

int main() {
  int x;
  if (!(std::cin >> x)) {
    return 1;
  }
  std::cout << x << "\n";
  return 0;
}
