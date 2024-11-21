import asyncio
import json
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from logger import get_logger

from .api import InstanceMonitor

logger = get_logger(__name__)

# Global instances
monitor: InstanceMonitor = None
redis_client: redis.Redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global monitor, redis_client
    load_dotenv()

    # Initialize Redis client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0
    )

    # Initialize and start monitor in background
    monitor = InstanceMonitor()
    asyncio.create_task(monitor.run())

    yield

    # Cancel the monitor task
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    redis_client.close()


app = FastAPI(title="Instance Monitor API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/stats/{stat_type}")
async def websocket_stats(websocket: WebSocket, stat_type: str):
    await websocket.accept()

    # Validate stat type
    valid_types = {"gpu", "cpu", "ssh"}
    if stat_type not in valid_types:
        await websocket.close(
            code=4000, reason=f"Invalid stat type. Must be one of: {valid_types}"
        )
        return

    try:
        # Subscribe to the appropriate Redis channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"{stat_type}_stats")

        # Listen for messages
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                await asyncio.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                print(f"Error processing message: {e}")
                break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(f"{stat_type}_stats")
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run("agent.main:app", host="0.0.0.0", port=8000, reload=True)
