# speed_test.py
import time


def fib(n):
    """A recursive (and slow) fibonacci function."""
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def run_benchmark():
    # We run fib(35). 
    # This number is high enough to take a few seconds
    # but not so high that it takes minutes.
    fib(40)


if __name__ == "__main__":
    print("Starting task...")

    start_time = time.time()

    run_benchmark()

    end_time = time.time()
    print(f"\nTotal time: {end_time - start_time:.2f} seconds")