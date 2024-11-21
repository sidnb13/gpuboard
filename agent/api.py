import asyncio
import json
import os
from datetime import datetime

import psutil
import pynvml
import redis.asyncio as redis
from dotenv import load_dotenv

from logger import get_logger

logger = get_logger(__name__)


class InstanceMonitor:
    def __init__(self, stream_interval=10):
        self.redis = redis.Redis(
            host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=0
        )
        self.pubsub = self.redis.pubsub()
        self.stream_interval = stream_interval

    async def get_gpu_stats(self, nvml_active=False):
        if not nvml_active:
            gpu_stats = [
                {
                    "gpu_id": 0,
                    "memory_total": 0,
                    "memory_used": 0,
                    "memory_free": 0,
                    "gpu_utilization": 0,
                    "memory_utilization": 0,
                    "temperature": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        else:
            device_count = pynvml.nvmlDeviceGetCount()
            gpu_stats = []

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)

                # Get memory info
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)

                # Get utilization info
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

                # Get temperature
                temp = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )

                gpu_stats.append(
                    {
                        "gpu_id": i,
                        "memory_total": memory.total,
                        "memory_used": memory.used,
                        "memory_free": memory.free,
                        "gpu_utilization": utilization.gpu,
                        "memory_utilization": utilization.memory,
                        "temperature": temp,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        stats_json = json.dumps(gpu_stats)
        logger.debug(f"GPU stats: {stats_json}")
        await self.redis.publish("gpu_stats", stats_json)

    async def get_cpu_stats(self):
        # Get system-wide stats
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get aggregate CPU utilization
        cpu_percent = psutil.cpu_percent(interval=1)

        cpu_stats = {
            "cpu_utilization": cpu_percent,
            "memory_total": memory.total,
            "memory_used": memory.used,
            "memory_free": memory.available,
            "memory_percent": memory.percent,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_free": disk.free,
            "disk_percent": disk.percent,
            "timestamp": datetime.now().isoformat(),
        }

        stats_json = json.dumps(cpu_stats)
        logger.debug(f"CPU stats: {stats_json}")
        await self.redis.publish("cpu_stats", stats_json)

    async def get_ssh_stats(self):
        ssh_stats = []

        try:
            # Get all network connections with status ESTABLISHED
            connections = psutil.net_connections(kind="inet")

            # Filter for SSH connections (port 22)
            for conn in connections:
                if conn.status == "ESTABLISHED" and conn.laddr.port == 22:
                    try:
                        # Get process info for this connection
                        process = psutil.Process(conn.pid)

                        ssh_stats.append(
                            {
                                "username": process.username(),
                                "pid": conn.pid,
                                "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}",
                                "status": conn.status,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        except (psutil.AccessDenied, psutil.Error) as e:
            logger.error(f"Error getting SSH stats: {e}")

        stats_json = json.dumps(ssh_stats)
        logger.debug(f"SSH stats: {stats_json}")
        await self.redis.publish("ssh_stats", stats_json)

        return ssh_stats

    async def run(self):
        try:
            pynvml.nvmlInit()
            nvml_active = True
        except Exception as _:
            logger.error("NVML library not found")
            nvml_active = False

        while True:
            try:
                await self.get_gpu_stats(nvml_active)
                await self.get_cpu_stats()
                await self.get_ssh_stats()
                await asyncio.sleep(self.stream_interval)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Shutting down GPU monitoring...")
                break

        pynvml.nvmlShutdown()


if __name__ == "__main__":
    load_dotenv()
    instance_monitor = InstanceMonitor()
    asyncio.run(instance_monitor.run())
