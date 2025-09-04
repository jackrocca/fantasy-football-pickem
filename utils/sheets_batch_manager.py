"""
Google Sheets Batch Manager for efficient API usage.
Implements batching, caching, and exponential backoff to avoid rate limits.
"""
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import pandas as pd
import gspread
from gspread.exceptions import APIError
import threading
from queue import Queue
import atexit


class SheetsBatchManager:
    """Manages batched operations for Google Sheets to avoid rate limits."""
    
    def __init__(self, spreadsheet, flush_interval: int = 30):
        self.spreadsheet = spreadsheet
        self.flush_interval = flush_interval
        
        # Write queues for each worksheet
        self.write_queues = defaultdict(list)
        self.append_queues = defaultdict(list)
        
        # Read cache with TTL
        self.read_cache = {}
        self.cache_ttl = timedelta(seconds=60)  # 1 minute cache
        
        # Threading for background flushing
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self._flush_thread.start()
        
        # Register cleanup on exit
        atexit.register(self.flush_all)
    
    def with_backoff(self, fn, max_tries: int = 6):
        """Execute function with exponential backoff on rate limits."""
        delay = 1.0
        for attempt in range(1, max_tries + 1):
            try:
                return fn()
            except APIError as e:
                status = getattr(e, "response", None) and e.response.status_code
                if status in (429, 503):  # rate limit or backend busy
                    if attempt == max_tries:
                        raise
                    jitter = random.uniform(0, 0.5)
                    sleep_time = delay + jitter
                    print(f"⏳ Rate limited, waiting {sleep_time:.1f}s (attempt {attempt}/{max_tries})")
                    time.sleep(sleep_time)
                    delay = min(delay * 2, 30)
                    continue
                raise
        raise RuntimeError("Exceeded retries")
    
    def _periodic_flush(self):
        """Background thread that flushes queues periodically."""
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            self.flush_all()
    
    def stop(self):
        """Stop the background flush thread."""
        self._stop_event.set()
        self._flush_thread.join(timeout=5)
        self.flush_all()
    
    def queue_update(self, worksheet_name: str, range_name: str, values: List[List]):
        """Queue a batch update for a worksheet."""
        with self._lock:
            self.write_queues[worksheet_name].append({
                "range": range_name,
                "values": values
            })
    
    def queue_append(self, worksheet_name: str, rows: List[List]):
        """Queue rows to append to a worksheet."""
        with self._lock:
            self.append_queues[worksheet_name].extend(rows)
    
    def flush_worksheet(self, worksheet_name: str):
        """Flush all pending operations for a specific worksheet."""
        with self._lock:
            # Handle batch updates
            if worksheet_name in self.write_queues and self.write_queues[worksheet_name]:
                updates = self.write_queues[worksheet_name]
                self.write_queues[worksheet_name] = []
                
                try:
                    worksheet = self.spreadsheet.worksheet(worksheet_name)
                    # Batch all updates into one request
                    batch_data = {
                        "valueInputOption": "RAW",
                        "data": updates
                    }
                    self.with_backoff(lambda: self.spreadsheet.values_batch_update(batch_data))
                    print(f"✅ Flushed {len(updates)} updates to {worksheet_name}")
                except Exception as e:
                    print(f"❌ Error flushing updates to {worksheet_name}: {e}")
                    # Re-queue on failure
                    self.write_queues[worksheet_name].extend(updates)
            
            # Handle appends
            if worksheet_name in self.append_queues and self.append_queues[worksheet_name]:
                rows = self.append_queues[worksheet_name]
                self.append_queues[worksheet_name] = []
                
                try:
                    worksheet = self.spreadsheet.worksheet(worksheet_name)
                    if rows:
                        self.with_backoff(lambda: worksheet.append_rows(rows))
                        print(f"✅ Appended {len(rows)} rows to {worksheet_name}")
                except Exception as e:
                    print(f"❌ Error appending to {worksheet_name}: {e}")
                    # Re-queue on failure
                    self.append_queues[worksheet_name].extend(rows)
    
    def flush_all(self):
        """Flush all pending operations for all worksheets."""
        worksheets_to_flush = set()
        
        with self._lock:
            worksheets_to_flush.update(self.write_queues.keys())
            worksheets_to_flush.update(self.append_queues.keys())
        
        for worksheet_name in worksheets_to_flush:
            self.flush_worksheet(worksheet_name)
    
    def cached_read(self, worksheet_name: str, cache_key: Optional[str] = None) -> pd.DataFrame:
        """Read worksheet with caching to avoid repeated reads."""
        cache_key = cache_key or worksheet_name
        now = datetime.now()
        
        # Check cache
        if cache_key in self.read_cache:
            cached_data, timestamp = self.read_cache[cache_key]
            if now - timestamp < self.cache_ttl:
                return cached_data
        
        # Perform read with backoff
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            records = self.with_backoff(lambda: worksheet.get_all_records())
            
            if records:
                df = pd.DataFrame(records)
                df = df.replace('', pd.NA)
            else:
                # Get headers if no records
                headers = self.with_backoff(lambda: worksheet.row_values(1)) if worksheet.row_count > 0 else []
                df = pd.DataFrame(columns=headers)
            
            # Cache the result
            self.read_cache[cache_key] = (df, now)
            return df
            
        except Exception as e:
            print(f"❌ Error reading {worksheet_name}: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame()
    
    def batch_read(self, worksheet_names: List[str]) -> Dict[str, pd.DataFrame]:
        """Read multiple worksheets efficiently."""
        results = {}
        
        for worksheet_name in worksheet_names:
            results[worksheet_name] = self.cached_read(worksheet_name)
        
        return results
    
    def invalidate_cache(self, worksheet_name: Optional[str] = None):
        """Invalidate cache for a specific worksheet or all."""
        if worksheet_name:
            self.read_cache.pop(worksheet_name, None)
        else:
            self.read_cache.clear()
    
    def update_dataframe(self, worksheet_name: str, df: pd.DataFrame):
        """Update entire worksheet with DataFrame content."""
        if df.empty:
            # Just update headers
            if not df.columns.empty:
                self.queue_update(worksheet_name, "A1", [df.columns.tolist()])
            return
        
        # Replace NaN with empty strings
        df_clean = df.fillna('').infer_objects(copy=False)
        
        # Prepare data with headers
        data_to_upload = [df_clean.columns.tolist()] + df_clean.values.tolist()
        
        # Queue the update
        self.queue_update(worksheet_name, "A1", data_to_upload)
        
        # Invalidate cache for this worksheet
        self.invalidate_cache(worksheet_name)


# Global instance
_batch_manager = None


def get_batch_manager(spreadsheet=None, flush_interval: int = 30) -> SheetsBatchManager:
    """Get or create the global batch manager instance."""
    global _batch_manager
    
    if _batch_manager is None and spreadsheet is not None:
        _batch_manager = SheetsBatchManager(spreadsheet, flush_interval)
    
    return _batch_manager


def shutdown_batch_manager():
    """Shutdown the batch manager and flush pending operations."""
    global _batch_manager
    
    if _batch_manager is not None:
        _batch_manager.stop()
        _batch_manager = None
