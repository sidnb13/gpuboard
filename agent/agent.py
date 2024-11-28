import asyncio
import json
from datetime import datetime
from typing import Optional

import aiohttp
import psutil
import pynvml
import redis.asyncio as redis

from logger import get_logger

logger = get_logger(__name__)


class Agent:
    def __init__(
        self,
        monitor_url: str,
        instance_id: str,
        backend_type: str,
        backend_api_key: str,
        monitor_api_key: str,
        name: Optional[str] = None,
        redis_client: redis.Redis = None,
        stream_interval: int = 10,
        registration_interval: int = 30,
    ):
        self.monitor_url = monitor_url
        self.instance_id = instance_id
        self.backend_type = backend_type
        self.backend_api_key = backend_api_key
        self.monitor_api_key = monitor_api_key
        self.name = name or instance_id
        self.redis = redis_client
        self.stats_monitor = InstanceMonitor(
            redis_client=redis_client,
            stream_interval=stream_interval,
            instance_id=instance_id,
        )
        self.is_registered = False
        self.registration_interval = (
            registration_interval  # seconds between registration attempts
        )

    async def register(self):
        """Register with the monitor service."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-Key": self.monitor_api_key}
                data = {
                    "backend_type": self.backend_type,
                    "backend_api_key": self.backend_api_key,
                    "name": self.name,
                }

                async with session.post(
                    f"{self.monitor_url}/register/{self.instance_id}",
                    headers=headers,
                    json=data,
                ) as response:
                    if response.status != 200:
                        logger.error(f"Registration failed: {await response.text()}")
                        return False

                    self.is_registered = True
                    logger.info(f"Successfully registered instance {self.instance_id}")
                    return True
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False

    async def deregister(self):
        """Deregister from the monitor service."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-Key": self.monitor_api_key}
                async with session.delete(
                    f"{self.monitor_url}/instances/{self.instance_id}", headers=headers
                ) as response:
                    if response.status != 200:
                        logger.error(f"Deregistration failed: {await response.text()}")
                        return False
                    self.is_registered = False
                    logger.info(
                        f"Successfully deregistered instance {self.instance_id}"
                    )
                    return True
        except Exception as e:
            logger.error(f"Deregistration error: {e}")
            return False

    async def registration_loop(self):
        """Continuously attempt registration until successful."""
        while not self.is_registered:
            if await self.register():
                break
            await asyncio.sleep(self.registration_interval)

    async def start_monitoring(self):
        """Start collecting and publishing stats."""
        if not self.redis:
            raise ValueError("Redis client not configured")
        await self.stats_monitor.run()

    async def start(self):
        """Start the agent with registration and monitoring."""
        registration_task = asyncio.create_task(self.registration_loop())
        monitoring_task = asyncio.create_task(self.start_monitoring())

        try:
            await asyncio.gather(registration_task, monitoring_task)
        except Exception as e:
            logger.error(f"Error in agent tasks: {e}")
            raise


class InstanceMonitor:
    def __init__(
        self,
        redis_client: redis.Redis = None,
        stream_interval: int = 10,
        instance_id: str = None,
    ):
        self.redis = redis_client
        self.instance_id = instance_id
        self.pubsub = self.redis.pubsub()
        self.stream_interval = stream_interval
        self.nvml_active = False

    async def initialize(self):
        """Initialize NVML if available."""
        try:
            pynvml.nvmlInit()
            self.nvml_active = True
            logger.info("NVML initialized successfully")
        except Exception as e:
            logger.warning(f"NVML initialization failed: {e}")
            self.nvml_active = False

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
        await self.redis.publish(f"stats/{self.instance_id}/gpu", stats_json)

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
        await self.redis.publish(f"stats/{self.instance_id}/cpu", stats_json)

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
        await self.redis.publish(f"stats/{self.instance_id}/ssh", stats_json)

        return ssh_stats

    async def run(self):
        """Main monitoring loop."""
        await self.initialize()

        try:
            while True:
                try:
                    await self.get_gpu_stats(self.nvml_active)
                    await self.get_cpu_stats()
                    await self.get_ssh_stats()
                    await asyncio.sleep(self.stream_interval)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down monitoring...")
        finally:
            if self.nvml_active:
                pynvml.nvmlShutdown()
