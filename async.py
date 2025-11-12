import asyncio


async def background_task():
    """A task that just prints a message every 0.5 seconds."""
    print("--- Background task STARTED ---")
    try:
        count = 1
        while True:
            print(f"Background: ...running... {count}")
            await asyncio.sleep(0.5) # Pauses, gives control back
            count += 1
    except asyncio.CancelledError:
        print("--- Background task CANCELLED ---")


async def fetch_user(id):
    print(f"Starting to fetch user {id}...")
    await asyncio.sleep(2) # Simulates a 2-second DB call
    print(f"Finished fetching user {id}.")
    return f"User {id}"

async def fetch_posts(id):
    print(f"Starting to fetch posts for {id}...")
    await asyncio.sleep(1) # Simulates a 1-second DB call
    print(f"Finished fetching posts for {id}.")
    return "User's Posts"

async def main():
    print("--- Running sequentially ---")
    
    bg_task = asyncio.create_task(background_task())

    
    await fetch_user(1) 
    
    await fetch_posts(1) 


    # await asyncio.gather(
    #     fetch_user(1),
    #     fetch_posts(1)
    # )

    bg_task.cancel()
    

asyncio.run(main())
