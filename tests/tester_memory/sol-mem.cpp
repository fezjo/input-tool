#include <cmath>
#include <iostream>
#include <sys/resource.h>
#include <unistd.h>
#include <vector>

void print_limits() {
  struct rlimit rl;

#define CHECK_LIMIT(resource)                                                  \
  if (getrlimit(resource, &rl) == 0)                                           \
    std::cerr << #resource << ": Soft: " << rl.rlim_cur                        \
              << " bytes, Hard: " << rl.rlim_max << " bytes\n";

  CHECK_LIMIT(RLIMIT_AS);
  CHECK_LIMIT(RLIMIT_DATA);
  CHECK_LIMIT(RLIMIT_RSS);
  CHECK_LIMIT(RLIMIT_STACK);
}

size_t consume_stack(float mb) {
  size_t bytes = static_cast<size_t>(mb * 1024 * 1024);

  // Allocate on stack (VLA-like via alloca)
  volatile char *buffer = (volatile char *)alloca(bytes);

  // Touch memory so it actually gets committed
  for (size_t i = 0; i < bytes; i += 4096)
    buffer[i] = 1;

  return bytes;
}

size_t consume_heap(float mb) {
  size_t bytes = static_cast<size_t>(mb * 1024 * 1024);

  std::vector<char> buffer(bytes);

  // Touch memory so it actually gets committed
  for (size_t i = 0; i < bytes; i += 4096)
    buffer[i] = 1;

  return bytes;
}

int main() {
  print_limits();

  float stack_mb, heap_mb;
  std::cin >> stack_mb >> heap_mb;

  size_t stack_used = consume_stack(stack_mb);
  size_t heap_used = consume_heap(heap_mb);

  std::cerr << "Stack consumed: " << stack_used << " bytes\n";
  std::cerr << "Heap consumed: " << heap_used << " bytes\n";

  return 0;
}