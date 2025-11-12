import concurrent.futures
import time
import os # To see the different Process IDs

def heavy_work(task_name):
    """
    A CPU-bound task that simulates heavy computation.
    """
    pid = os.getpid()
    print(f"[PID: {pid}] {task_name}: Starting CPU-heavy work...")
    
    # A CPU-bound task (not I/O like time.sleep)
    count = 0
    for i in range(200_000_000):
        count += 1
        
    print(f"[PID: {pid}] {task_name}: Finished.")
    return f"{task_name} is done"

# You MUST protect your main code like this for multiprocessing
if __name__ == "__main__":
    
    start_time = time.time()
    
    # 1. Create a Process Pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:            #  ThreadPoolExecutor or ProcessPoolExecutor
        
        print("Main: Submitting tasks to the pool...\n")
        
        # 2. Submit tasks to the pool
        future1 = executor.submit(heavy_work, "Task-A")
        future2 = executor.submit(heavy_work, "Task-B")
        future3 = executor.submit(heavy_work, "Task-C")
        future4 = executor.submit(heavy_work, "Task-D")

        # 3. Get results (this waits for them to finish)
        print(future1.result())
        print(future2.result())
        print(future3.result())
        print(future4.result())

    end_time = time.time()
    print(f"\nTotal time: {end_time - start_time:.2f} seconds")





# import concurrent.futures
# import time
# import threading # To get thread name

# def heavy_work(task_name):
#     """
#     A CPU-bound task that counts to a large number.
#     """
#     # Get the name of the current thread
#     thread_name = threading.current_thread().name
#     print(f"[{thread_name}] {task_name}: Starting CPU-heavy work...")
    
#     # This is a CPU-bound task.
#     # The thread will HOLD the GIL while doing this.
#     count = 0
#     for i in range(200_000_000):
#         count += 1
        
#     print(f"[{thread_name}] {task_name}: Finished.")
#     return f"{task_name} is done"

# # No need for the __name__ == "__main__" guard with threading
# start_time = time.time()

# # 1. Create a Thread Pool
# with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    
#     print("Main: Submitting tasks to the pool...\n")
    
#     # 2. Submit tasks to the pool
#     future1 = executor.submit(heavy_work, "Task-A")
#     future2 = executor.submit(heavy_work, "Task-B")

#     # 3. Get results (this waits for them to finish)
#     print(future1.result())
#     print(future2.result())

# end_time = time.time()
# print(f"\nTotal time: {end_time - start_time:.2f} seconds")