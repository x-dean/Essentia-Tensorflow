#!/usr/bin/env python3
"""
Configuration monitoring and metrics collection
"""

import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class ConfigChangeEvent:
    """Configuration change event"""
    timestamp: datetime
    config_name: str
    change_type: str  # 'modified', 'added', 'removed'
    old_hash: Optional[str]
    new_hash: Optional[str]
    details: Dict[str, Any]

@dataclass
class ConfigMetrics:
    """Configuration metrics"""
    config_name: str
    load_count: int
    error_count: int
    last_load_time: Optional[datetime]
    last_error_time: Optional[datetime]
    average_load_time: float
    validation_errors: List[str]

class ConfigMonitor:
    """Monitor configuration changes and collect metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.change_history: deque = deque(maxlen=max_history)
        self.metrics: Dict[str, ConfigMetrics] = defaultdict(
            lambda: ConfigMetrics(
                config_name="",
                load_count=0,
                error_count=0,
                last_load_time=None,
                last_error_time=None,
                average_load_time=0.0,
                validation_errors=[]
            )
        )
        self.config_hashes: Dict[str, str] = {}
        self.watched_paths: Set[Path] = set()
        self.start_time = datetime.now()
    
    def record_config_load(self, config_name: str, config_data: Dict[str, Any], 
                          load_time: float, success: bool = True, errors: List[str] = None):
        """Record a configuration load event"""
        now = datetime.now()
        config_hash = self._compute_hash(config_data)
        
        # Update metrics
        metrics = self.metrics[config_name]
        metrics.config_name = config_name
        metrics.load_count += 1
        metrics.last_load_time = now
        
        if not success:
            metrics.error_count += 1
            metrics.last_error_time = now
            if errors:
                metrics.validation_errors.extend(errors)
        
        # Update average load time
        if metrics.average_load_time == 0.0:
            metrics.average_load_time = load_time
        else:
            metrics.average_load_time = (metrics.average_load_time + load_time) / 2
        
        # Check for changes
        old_hash = self.config_hashes.get(config_name)
        if old_hash != config_hash:
            change_type = 'modified' if old_hash else 'added'
            self._record_change(config_name, change_type, old_hash, config_hash, config_data)
            self.config_hashes[config_name] = config_hash
    
    def record_config_validation(self, config_name: str, is_valid: bool, errors: List[str] = None):
        """Record configuration validation results"""
        metrics = self.metrics[config_name]
        if not is_valid and errors:
            metrics.validation_errors.extend(errors)
            metrics.error_count += 1
            metrics.last_error_time = datetime.now()
    
    def _record_change(self, config_name: str, change_type: str, old_hash: Optional[str], 
                      new_hash: Optional[str], config_data: Dict[str, Any]):
        """Record a configuration change"""
        event = ConfigChangeEvent(
            timestamp=datetime.now(),
            config_name=config_name,
            change_type=change_type,
            old_hash=old_hash,
            new_hash=new_hash,
            details={
                'config_keys': list(config_data.keys()) if config_data else [],
                'config_size': len(json.dumps(config_data)) if config_data else 0
            }
        )
        
        self.change_history.append(event)
        logger.info(f"Configuration change detected: {config_name} - {change_type}")
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash of configuration data"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def get_change_history(self, config_name: Optional[str] = None, 
                          since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get configuration change history"""
        history = []
        
        for event in self.change_history:
            if config_name and event.config_name != config_name:
                continue
            if since and event.timestamp < since:
                continue
            
            history.append(asdict(event))
        
        return history
    
    def get_metrics(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration metrics"""
        if config_name:
            if config_name not in self.metrics:
                return {}
            metrics = self.metrics[config_name]
            return {
                config_name: {
                    'load_count': metrics.load_count,
                    'error_count': metrics.error_count,
                    'last_load_time': metrics.last_load_time.isoformat() if metrics.last_load_time else None,
                    'last_error_time': metrics.last_error_time.isoformat() if metrics.last_error_time else None,
                    'average_load_time': metrics.average_load_time,
                    'validation_errors': metrics.validation_errors[-10:],  # Last 10 errors
                    'success_rate': (metrics.load_count - metrics.error_count) / max(metrics.load_count, 1) * 100
                }
            }
        else:
            return {
                name: {
                    'load_count': metrics.load_count,
                    'error_count': metrics.error_count,
                    'last_load_time': metrics.last_load_time.isoformat() if metrics.last_load_time else None,
                    'last_error_time': metrics.last_error_time.isoformat() if metrics.last_error_time else None,
                    'average_load_time': metrics.average_load_time,
                    'validation_errors_count': len(metrics.validation_errors),
                    'success_rate': (metrics.load_count - metrics.error_count) / max(metrics.load_count, 1) * 100
                }
                for name, metrics in self.metrics.items()
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall configuration health status"""
        total_loads = sum(m.load_count for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        recent_changes = len([e for e in self.change_history 
                            if e.timestamp > datetime.now() - timedelta(hours=1)])
        
        return {
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'total_config_loads': total_loads,
            'total_errors': total_errors,
            'overall_success_rate': (total_loads - total_errors) / max(total_loads, 1) * 100,
            'recent_changes_last_hour': recent_changes,
            'monitored_configs': len(self.metrics),
            'change_history_size': len(self.change_history),
            'status': 'healthy' if total_errors == 0 else 'degraded' if total_errors < total_loads * 0.1 else 'unhealthy'
        }
    
    def clear_history(self):
        """Clear change history"""
        self.change_history.clear()
        logger.info("Configuration change history cleared")
    
    def reset_metrics(self, config_name: Optional[str] = None):
        """Reset metrics for a specific config or all configs"""
        if config_name:
            if config_name in self.metrics:
                del self.metrics[config_name]
                logger.info(f"Metrics reset for {config_name}")
        else:
            self.metrics.clear()
            logger.info("All configuration metrics reset")

# Global monitor instance
config_monitor = ConfigMonitor()
