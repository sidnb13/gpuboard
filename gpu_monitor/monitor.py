import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from logger import get_logger

from .backends import Backend, BackendFactory, BackendType

logger = get_logger(__name__)


class InstanceConfig:
    """Configuration for a monitored instance."""

    def __init__(self, backend: Backend, instance_id: str, name: str = None):
        self.backend = backend
        self.instance_id = instance_id
        self.name = name or instance_id
        self.last_activity_time = datetime.now()
        self.last_heartbeat = datetime.now()  # Track last stats update


class InstanceStatusType(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class InstanceStatus(BaseModel):
    status: InstanceStatusType
    message: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class ClusterMonitor:
    def __init__(
        self,
        idle_shutdown_minutes: int = 30,
        warning_minutes: int = 5,
        check_interval_seconds: int = 60,
        dry_run: bool = False,
        agent_url: str = "http://localhost:8000",
        slack_token: Optional[str] = None,
        slack_channel: Optional[str] = None,
    ):
        self.idle_shutdown_minutes = idle_shutdown_minutes
        self.warning_minutes = warning_minutes
        self.check_interval = check_interval_seconds
        self.dry_run = dry_run
        self.agent_url = agent_url
        self.logger = logging.getLogger(__name__)
        self.known_agents: Set[str] = set()

        # Slack configuration
        self.slack = AsyncWebClient(token=slack_token) if slack_token else None
        self.slack_channel = slack_channel

        # Track stats per instance
        self.instances: Dict[str, InstanceConfig] = {}
        self.instance_stats: Dict[str, Dict] = defaultdict(dict)
        self.ws_base_url = agent_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        )

    async def get_instance_status(self, instance_id: str) -> InstanceStatus:
        instance = self.instances.get(instance_id)
        if not instance:
            return InstanceStatus(
                status=InstanceStatus.status.OFFLINE,
                message="Unknown instance",
                last_heartbeat=None,
                last_activity=None,
            )

        now = datetime.now()
        heartbeat_elapsed = (now - instance.last_heartbeat).total_seconds()

        if heartbeat_elapsed > self.check_interval:
            status = InstanceStatusType.OFFLINE
            message = f"No heartbeat received in {heartbeat_elapsed} seconds"
        else:
            status = InstanceStatusType.ONLINE
            message = f"Last update received {heartbeat_elapsed} seconds ago"

        return InstanceStatus(
            status=status,
            message=message,
            last_heartbeat=instance.last_heartbeat,
            last_activity=instance.last_activity_time,
        )

    async def register_agent(
        self,
        instance_id: str,
        backend_type: str,
        backend_api_key: str,
        name: Optional[str] = None,
    ):
        """Register a new agent/instance with the monitor."""
        try:
            # Convert string backend type to enum
            backend_enum = BackendType(backend_type.lower())

            # Create backend instance using factory
            backend = BackendFactory.create_backend(
                backend_type=backend_enum, api_key=backend_api_key
            )

            # Create instance config
            instance_config = InstanceConfig(
                backend=backend, instance_id=instance_id, name=name
            )

            # Add to tracked instances
            self.instances[instance_id] = instance_config
            self.instance_stats[instance_id] = {}

            self.logger.info(f"Successfully registered instance {instance_id} ({name})")
            return True

        except ValueError as e:
            self.logger.error(f"Failed to register instance {instance_id}: {e}")
            raise ValueError(f"Invalid backend type: {backend_type}")
        except Exception as e:
            self.logger.error(f"Failed to register instance {instance_id}: {e}")
            raise

    async def notify_users(
        self, instance_id: str, users: List[str], minutes_remaining: int, ts: str = None
    ) -> Optional[str]:
        """
        Notify users of impending shutdown via Slack.
        Returns the timestamp of the message for potential updates.
        """
        if not self.slack or not self.slack_channel:
            self.logger.warning("Slack not configured, skipping notification")
            return None

        instance = self.instances[instance_id]
        message = (
            f"⚠️ *Instance Shutdown Warning* ⚠️\n"
            f"Instance {instance.name} ({instance_id}) will shut down in {minutes_remaining} minutes due to inactivity.\n"
            f"Active users: {', '.join(users)}\n"
            f"Please save your work and log out if you're done."
        )

        try:
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would send Slack message: {message}")
                return None

            if ts:
                # Update existing message
                response = await self.slack.chat_update(
                    channel=self.slack_channel, ts=ts, text=message, unfurl_links=False
                )
            else:
                # Send new message
                response = await self.slack.chat_postMessage(
                    channel=self.slack_channel, text=message, unfurl_links=False
                )
            return response["ts"]  # Return message timestamp for future updates
        except SlackApiError as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return None

    async def update_shutdown_status(self, instance_id: str, status: str, ts: str):
        """Update Slack message with shutdown status."""
        if not self.slack or not self.slack_channel or not ts:
            return

        instance = self.instances.get(instance_id)
        if not instance:
            return

        message = (
            f"🔄 *Instance Shutdown Status* 🔄\n"
            f"Instance {instance.name} ({instance_id}): {status}"
        )

        try:
            if not self.dry_run:
                await self.slack.chat_update(
                    channel=self.slack_channel, ts=ts, text=message, unfurl_links=False
                )
        except SlackApiError as e:
            self.logger.error(f"Failed to update Slack message: {e}")

    async def shutdown_instance(self, instance_id: str):
        """Shutdown specific instance using its backend."""
        instance = self.instances[instance_id]

        if self.dry_run:
            self.logger.warning(
                f"DRY RUN: Would shutdown instance {instance.name} ({instance_id})"
            )
            del self.instances[instance_id]
            return

        try:
            self.logger.info(
                f"Initiating shutdown for instance {instance.name} ({instance_id})"
            )
            response = instance.backend.stop_instance(instance_id)
            del self.instances[instance_id]
            self.logger.info(f"Shutdown response: {response}")
        except Exception as e:
            self.logger.error(f"Failed to shutdown instance {instance_id}: {e}")
            del self.instances[instance_id]
            raise

    async def check_active_processes(self, stats: Dict) -> bool:
        """Check if there are any active GPU processes."""
        try:
            gpu_stats = stats.get("gpu_stats", [])
            if not gpu_stats:
                return False

            # Check if any GPU has significant utilization
            for gpu in gpu_stats:
                if (
                    gpu.get("gpu_utilization", 0) > 5
                    or gpu.get("memory_utilization", 0) > 5
                ):
                    self.logger.info(f"Active GPU processes detected: {gpu}")
                    return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking GPU processes: {e}")
            return False

    async def get_ssh_sessions(self, stats: Dict) -> List[str]:
        """Get list of users with active SSH sessions."""
        try:
            ssh_stats = stats.get("ssh_stats", [])
            users = [
                session.get("username")
                for session in ssh_stats
                if session.get("username")
            ]
            return list(set(users))  # Remove duplicates
        except Exception as e:
            self.logger.error(f"Error getting SSH sessions: {e}")
            return []

    async def check_user_activity(self, stats: Dict) -> bool:
        """
        Check if a user has recent activity by monitoring CPU usage.
        Returns True if there's significant activity.
        """
        try:
            cpu_stats = stats.get("cpu_stats", {})
            if not cpu_stats:
                return False

            # Consider system active if CPU utilization is above threshold
            cpu_utilization = cpu_stats.get("cpu_utilization", 0)
            if cpu_utilization > 10:  # 10% CPU usage threshold
                self.logger.info(f"Active CPU usage detected: {cpu_utilization}%")
                return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking user activity: {e}")
            return False

    async def process_stats(self, instance_id: str, stat_type: str, data: dict):
        """Process incoming stats from an agent."""
        if instance_id not in self.instances:
            self.logger.warning(f"Received stats for unknown instance: {instance_id}")
            return

        self.instance_stats[instance_id][f"{stat_type}_stats"] = data
        self.instances[instance_id].last_heartbeat = datetime.now()

    async def monitor_loop(self):
        """Main monitoring loop for all instances."""
        shutdown_queue = {}  # Track instances pending shutdown: {instance_id: slack_ts}

        while True:
            try:
                # Process pending shutdowns first
                for instance_id, (start_time, slack_ts) in list(shutdown_queue.items()):
                    if instance_id not in self.instances:
                        continue

                    elapsed_time = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed_time >= self.warning_minutes:
                        try:
                            await self.update_shutdown_status(
                                instance_id, "Initiating shutdown...", slack_ts
                            )
                            await self.shutdown_instance(instance_id)
                            await self.update_shutdown_status(
                                instance_id, "Shutdown completed", slack_ts
                            )
                        except Exception as e:
                            await self.update_shutdown_status(
                                instance_id, f"Shutdown failed: {str(e)}", slack_ts
                            )
                        finally:
                            del shutdown_queue[instance_id]

                # Check for new instances that need shutdown
                for instance_id, instance in self.instances.items():
                    if instance_id in shutdown_queue:
                        continue  # Skip instances already pending shutdown

                    stats = self.instance_stats[instance_id]
                    active_processes = await self.check_active_processes(stats)
                    ssh_users = await self.get_ssh_sessions(stats)
                    has_activity = active_processes

                    logger.debug(f"Instance {instance_id} has activity: {has_activity}")

                    # Check for user activity
                    if not has_activity and ssh_users:
                        has_activity = await self.check_user_activity(stats)
                        if has_activity:
                            instance.last_activity_time = datetime.now()

                    if not has_activity:
                        idle_time = datetime.now() - instance.last_activity_time
                        idle_minutes = idle_time.total_seconds() / 60

                        if idle_minutes >= self.idle_shutdown_minutes:
                            # Initiate shutdown sequence
                            slack_ts = await self.notify_users(
                                instance_id, ssh_users, self.warning_minutes
                            )
                            shutdown_queue[instance_id] = (datetime.now(), slack_ts)
                            logger.debug(
                                f"Instance {instance_id} queued for shutdown in {self.warning_minutes} minutes"
                            )

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")

            await asyncio.sleep(self.check_interval)
