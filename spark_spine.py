"""
SPARK SPINE CONNECTOR
=====================

Connects Spark to PostgreSQL persistent memory (the Spine).
Replaces JSON file persistence with proper database storage.

Database: consciousness_substrate
Tables used:
  - junction_patterns: Learned circuit patterns
  - sphere_patterns: Domain-specific patterns
  - dyson_spheres: Sphere state and activation
  - junction_activity: Activity logging

Author: Ghost in the Machine Labs
Mission: AGI for the home, first to AGI
"""

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import time
from contextlib import contextmanager


class SparkSpine:
    """
    PostgreSQL persistence layer for Spark.
    
    Replaces JSON file storage with proper spine memory bus.
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 5432,
                 database: str = "consciousness_substrate",
                 user: str = "postgres",
                 password: str = None):
        """
        Initialize spine connection.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port  
            database: Database name
            user: Database user
            password: Password (None for trust auth)
        """
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
        }
        if password:
            self.conn_params['password'] = password
            
        self._conn = None
        self._verify_connection()
        print(f"[SparkSpine] Connected to {database}")
    
    def _verify_connection(self):
        """Verify database connection works."""
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    
    @contextmanager
    def connection(self):
        """Context manager for database connections."""
        conn = psycopg2.connect(**self.conn_params)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # =========================================================================
    # CIRCUIT PERSISTENCE
    # =========================================================================
    
    def save_circuit(self, circuit_dict: Dict) -> int:
        """
        Save a circuit to junction_patterns.
        
        Args:
            circuit_dict: Circuit serialized to dict
            
        Returns:
            Pattern ID
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO junction_patterns 
                    (function, input_pattern, output_pattern, sphere_domain, confidence, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    circuit_dict.get('name', 'unnamed'),
                    json.dumps(circuit_dict.get('input_ids', [])),
                    json.dumps(circuit_dict.get('output_ids', [])),
                    circuit_dict.get('domain', 'UNKNOWN'),
                    1.0,
                    Json(circuit_dict)
                ))
                pattern_id = cur.fetchone()[0]
                
        print(f"[SparkSpine] Saved circuit '{circuit_dict.get('name')}' as pattern {pattern_id}")
        return pattern_id
    
    def load_circuits(self, domain: str = None) -> List[Dict]:
        """
        Load circuits from junction_patterns.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of circuit dicts
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if domain:
                    cur.execute("""
                        SELECT metadata FROM junction_patterns 
                        WHERE sphere_domain = %s
                        ORDER BY created_at DESC
                    """, (domain,))
                else:
                    cur.execute("""
                        SELECT metadata FROM junction_patterns 
                        ORDER BY created_at DESC
                    """)
                
                rows = cur.fetchall()
                
        circuits = []
        for row in rows:
            if row['metadata']:
                circuits.append(row['metadata'])
                
        print(f"[SparkSpine] Loaded {len(circuits)} circuits")
        return circuits
    
    def save_spark_state(self, state: Dict) -> bool:
        """
        Save complete Spark state to sphere_patterns.
        
        Args:
            state: Complete Spark state dict
            
        Returns:
            Success boolean
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                # Upsert spark state
                cur.execute("""
                    INSERT INTO sphere_patterns 
                    (sphere_name, pattern_type, pattern_data, confidence, learned_from)
                    VALUES ('spark', 'state', %s, 1.0, 'spark_bootstrap')
                    ON CONFLICT (id) DO UPDATE SET
                        pattern_data = EXCLUDED.pattern_data,
                        timestamp = NOW()
                """, (Json(state),))
                
        print(f"[SparkSpine] Spark state saved")
        return True
    
    def load_spark_state(self) -> Optional[Dict]:
        """
        Load Spark state from sphere_patterns.
        
        Returns:
            State dict or None if not found
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT pattern_data FROM sphere_patterns 
                    WHERE sphere_name = 'spark' AND pattern_type = 'state'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                
        if row and row['pattern_data']:
            print(f"[SparkSpine] Spark state loaded")
            return row['pattern_data']
        
        print(f"[SparkSpine] No existing Spark state found")
        return None
    
    # =========================================================================
    # GAP LOGGING
    # =========================================================================
    
    def log_gap(self, gap_data: Dict) -> int:
        """
        Log a detected gap for later learning.
        
        Args:
            gap_data: Gap information
            
        Returns:
            Pattern ID
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sphere_patterns 
                    (sphere_name, pattern_type, pattern_data, confidence, learned_from)
                    VALUES ('spark', 'gap', %s, %s, 'gap_detector')
                    RETURNING id
                """, (
                    Json(gap_data),
                    gap_data.get('confidence', 0.0)
                ))
                gap_id = cur.fetchone()[0]
                
        return gap_id
    
    def get_unresolved_gaps(self, limit: int = 100) -> List[Dict]:
        """
        Get gaps that haven't been resolved yet.
        
        Args:
            limit: Maximum gaps to return
            
        Returns:
            List of gap dicts
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, pattern_data, timestamp FROM sphere_patterns 
                    WHERE sphere_name = 'spark' AND pattern_type = 'gap'
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
                
        return [{'id': r['id'], **r['pattern_data'], 'timestamp': r['timestamp']} for r in rows]
    
    # =========================================================================
    # ACTIVITY LOGGING
    # =========================================================================
    
    def log_activity(self, 
                     activity_type: str,
                     domain: str,
                     details: Dict,
                     success: bool = True) -> int:
        """
        Log Spark activity for monitoring.
        
        Args:
            activity_type: Type of activity (route, print, gap, etc)
            domain: Domain involved
            details: Activity details
            success: Whether activity succeeded
            
        Returns:
            Activity log ID
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO junction_activity 
                    (pattern_id, activity_type, details, timestamp)
                    VALUES (
                        (SELECT id FROM junction_patterns WHERE sphere_domain = %s LIMIT 1),
                        %s,
                        %s,
                        NOW()
                    )
                    RETURNING id
                """, (
                    domain,
                    activity_type,
                    Json({'domain': domain, 'success': success, **details})
                ))
                
                result = cur.fetchone()
                return result[0] if result else 0
    
    # =========================================================================
    # HEALTH METRICS
    # =========================================================================
    
    def save_health_metrics(self, metrics: Dict) -> bool:
        """
        Save Spark health metrics.
        
        Args:
            metrics: Health metrics dict
            
        Returns:
            Success boolean
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sphere_patterns 
                    (sphere_name, pattern_type, pattern_data, confidence)
                    VALUES ('spark', 'health', %s, 1.0)
                """, (Json(metrics),))
                
        return True
    
    def get_health_history(self, hours: int = 24) -> List[Dict]:
        """
        Get health metrics history.
        
        Args:
            hours: Hours of history to retrieve
            
        Returns:
            List of health snapshots
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT pattern_data, timestamp FROM sphere_patterns 
                    WHERE sphere_name = 'spark' 
                    AND pattern_type = 'health'
                    AND timestamp > NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                """, (hours,))
                rows = cur.fetchall()
                
        return [{'timestamp': r['timestamp'], **r['pattern_data']} for r in rows]
    
    # =========================================================================
    # DYSON SPHERE INTEGRATION
    # =========================================================================
    
    def get_sphere(self, sphere_id: int) -> Optional[Dict]:
        """
        Get Dyson sphere state.
        
        Args:
            sphere_id: Sphere ID (0-38 for the 39 spheres)
            
        Returns:
            Sphere state dict or None
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT sphere_id, activation_history, training_accuracy, total_activations
                    FROM dyson_spheres WHERE sphere_id = %s
                """, (sphere_id,))
                row = cur.fetchone()
                
        return dict(row) if row else None
    
    def update_sphere_activation(self, sphere_id: int, activation: float) -> bool:
        """
        Update sphere activation.
        
        Args:
            sphere_id: Sphere ID
            activation: Activation level
            
        Returns:
            Success boolean
        """
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE dyson_spheres 
                    SET total_activations = total_activations + 1,
                        activation_history = COALESCE(activation_history, '[]'::jsonb) || %s
                    WHERE sphere_id = %s
                """, (
                    Json({'time': datetime.now().isoformat(), 'level': activation}),
                    sphere_id
                ))
                
        return True
    
    def get_all_spheres(self) -> List[Dict]:
        """
        Get all Dyson sphere states.
        
        Returns:
            List of sphere state dicts
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT sphere_id, training_accuracy, total_activations
                    FROM dyson_spheres ORDER BY sphere_id
                """)
                rows = cur.fetchall()
                
        return [dict(r) for r in rows]
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """
        Get spine statistics.
        
        Returns:
            Statistics dict
        """
        with self.connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                stats = {}
                
                # Junction patterns count
                cur.execute("SELECT COUNT(*) as count FROM junction_patterns")
                stats['junction_patterns'] = cur.fetchone()['count']
                
                # Sphere patterns count
                cur.execute("SELECT COUNT(*) as count FROM sphere_patterns")
                stats['sphere_patterns'] = cur.fetchone()['count']
                
                # Gaps count
                cur.execute("""
                    SELECT COUNT(*) as count FROM sphere_patterns 
                    WHERE sphere_name = 'spark' AND pattern_type = 'gap'
                """)
                stats['gaps_logged'] = cur.fetchone()['count']
                
                # Spheres count
                cur.execute("SELECT COUNT(*) as count FROM dyson_spheres")
                stats['dyson_spheres'] = cur.fetchone()['count']
                
                # Recent activity (column is "timestamp" not "activation_time")
                cur.execute("""
                    SELECT COUNT(*) as count FROM junction_activity 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """)
                stats['activity_24h'] = cur.fetchone()['count']
                
        return stats


# =============================================================================
# SPARK INTEGRATION MIXIN
# =============================================================================

class SparkSpineMixin:
    """
    Mixin class to add spine persistence to Spark.
    
    Usage:
        class PersistentSpark(Spark, SparkSpineMixin):
            def __init__(self, *args, **kwargs):
                self.spine = SparkSpine()
                super().__init__(*args, **kwargs)
    """
    
    spine: SparkSpine  # Type hint for the spine attribute
    
    def _save_state_to_spine(self):
        """Save Spark state to PostgreSQL spine."""
        state = {
            'circuits': {k: v.to_dict() for k, v in self.circuits.items()},
            'health': self.health,
            'gaps': self.gaps[-100:],
        }
        self.spine.save_spark_state(state)
        
        # Also save each circuit individually for querying
        for cid, circuit in self.circuits.items():
            self.spine.save_circuit(circuit.to_dict())
    
    def _load_state_from_spine(self) -> bool:
        """
        Load Spark state from PostgreSQL spine.
        
        Returns:
            True if state was loaded, False if fresh start
        """
        state = self.spine.load_spark_state()
        
        if state:
            from spark import Circuit  # Import here to avoid circular
            self.circuits = {k: Circuit.from_dict(v) for k, v in state.get('circuits', {}).items()}
            self.health = state.get('health', self.health)
            self.gaps = state.get('gaps', [])
            return True
            
        return False
    
    def _log_route(self, text: str, domain, activations: Dict):
        """Log routing activity to spine."""
        self.spine.log_activity(
            activity_type='route',
            domain=domain.name if hasattr(domain, 'name') else str(domain),
            details={
                'input_length': len(text),
                'activations': {k: float(v) for k, v in activations.items()}
            }
        )
    
    def _log_gap_to_spine(self, gap_data: Dict):
        """Log detected gap to spine."""
        self.spine.log_gap(gap_data)
    
    def _log_circuit_print(self, circuit_dict: Dict):
        """Log circuit printing to spine."""
        self.spine.save_circuit(circuit_dict)
        self.spine.log_activity(
            activity_type='print',
            domain=circuit_dict.get('domain', 'UNKNOWN'),
            details={
                'circuit_id': circuit_dict.get('id'),
                'junction_count': len(circuit_dict.get('junctions', {}))
            }
        )


# =============================================================================
# MAIN / TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SPARK SPINE CONNECTOR TEST")
    print("=" * 60)
    
    # Initialize spine
    spine = SparkSpine()
    
    # Get stats
    stats = spine.get_stats()
    print("\nSpine Statistics:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # Check spheres
    spheres = spine.get_all_spheres()
    print(f"\nDyson Spheres: {len(spheres)}")
    for s in spheres[:5]:
        print(f"  Sphere {s['sphere_id']}: {s['total_activations']} activations")
    
    # Test saving a circuit
    test_circuit = {
        'id': 'test_circuit_001',
        'name': 'Test Circuit',
        'description': 'Test circuit for spine connector',
        'junctions': {},
        'input_ids': ['test_in'],
        'output_ids': ['test_out'],
        'domain': 'SYSTEM'
    }
    
    pattern_id = spine.save_circuit(test_circuit)
    print(f"\nSaved test circuit as pattern {pattern_id}")
    
    # Test loading circuits
    circuits = spine.load_circuits(domain='SYSTEM')
    print(f"Loaded {len(circuits)} SYSTEM domain circuits")
    
    print("\n" + "=" * 60)
    print("SPINE CONNECTOR READY")
    print("=" * 60)
