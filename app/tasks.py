"""
Task definitions for SQLAudit-Env.
Each task has queries, schema, and ground-truth answers for grading.
"""
from __future__ import annotations
from typing import Dict, Any, List
from app.models import SchemaTable

# ─── SHARED SCHEMA ────────────────────────────────────────────────────────────

SHARED_SCHEMA = {
    "users": SchemaTable(
        name="users",
        columns=[
            {"name": "id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "email", "type": "VARCHAR(255)", "nullable": "NO", "pii": "YES"},
            {"name": "full_name", "type": "VARCHAR(255)", "nullable": "YES", "pii": "YES"},
            {"name": "ssn", "type": "CHAR(11)", "nullable": "YES", "pii": "YES"},
            {"name": "password_hash", "type": "VARCHAR(255)", "nullable": "NO", "pii": "YES"},
            {"name": "created_at", "type": "TIMESTAMP", "nullable": "NO", "pii": "NO"},
            {"name": "role", "type": "VARCHAR(50)", "nullable": "NO", "pii": "NO"},
        ],
        indexes=["PRIMARY KEY (id)", "UNIQUE (email)"],
        row_estimate=500000,
    ),
    "orders": SchemaTable(
        name="orders",
        columns=[
            {"name": "id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "user_id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "status", "type": "VARCHAR(50)", "nullable": "NO", "pii": "NO"},
            {"name": "total_amount", "type": "DECIMAL(12,2)", "nullable": "NO", "pii": "NO"},
            {"name": "created_at", "type": "TIMESTAMP", "nullable": "NO", "pii": "NO"},
        ],
        indexes=["PRIMARY KEY (id)", "INDEX idx_user_id (user_id)"],
        row_estimate=5000000,
    ),
    "products": SchemaTable(
        name="products",
        columns=[
            {"name": "id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "name", "type": "VARCHAR(255)", "nullable": "NO", "pii": "NO"},
            {"name": "price", "type": "DECIMAL(10,2)", "nullable": "NO", "pii": "NO"},
            {"name": "category_id", "type": "BIGINT", "nullable": "YES", "pii": "NO"},
            {"name": "description", "type": "TEXT", "nullable": "YES", "pii": "NO"},
        ],
        indexes=["PRIMARY KEY (id)"],
        row_estimate=50000,
    ),
    "order_items": SchemaTable(
        name="order_items",
        columns=[
            {"name": "id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "order_id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "product_id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "quantity", "type": "INT", "nullable": "NO", "pii": "NO"},
            {"name": "unit_price", "type": "DECIMAL(10,2)", "nullable": "NO", "pii": "NO"},
        ],
        indexes=["PRIMARY KEY (id)", "INDEX idx_order_id (order_id)"],
        row_estimate=25000000,
    ),
    "audit_logs": SchemaTable(
        name="audit_logs",
        columns=[
            {"name": "id", "type": "BIGINT", "nullable": "NO", "pii": "NO"},
            {"name": "user_id", "type": "BIGINT", "nullable": "YES", "pii": "NO"},
            {"name": "action", "type": "VARCHAR(100)", "nullable": "NO", "pii": "NO"},
            {"name": "ip_address", "type": "VARCHAR(45)", "nullable": "YES", "pii": "YES"},
            {"name": "created_at", "type": "TIMESTAMP", "nullable": "NO", "pii": "NO"},
        ],
        indexes=["PRIMARY KEY (id)"],
        row_estimate=100000000,
    ),
}

# ─── TASK EASY ─────────────────────────────────────────────────────────────────

TASK_EASY = {
    "id": "task_easy",
    "name": "SQL Security Scan (Easy)",
    "difficulty": "easy",
    "max_steps": 20,
    "phase_sequence": ["scanning"],
    "queries": [
        # 0: SQL Injection - classic string concat
        "SELECT * FROM users WHERE email = '" + "' + user_input + '",
        # 1: Safe parameterized query
        "SELECT id, email, role FROM users WHERE id = %s AND role = %s",
        # 2: SQL Injection - UNION attack vector
        "SELECT name, price FROM products WHERE id = " + str(1) + " UNION SELECT username, password FROM admin--",
        # 3: Safe query with no issues
        "SELECT COUNT(*) as total FROM orders WHERE status = 'completed' AND created_at >= NOW() - INTERVAL 30 DAY",
        # 4: Stored-proc injection risk
        "EXEC sp_executesql N'SELECT * FROM users WHERE role = ''' + @role + ''''"
    ],
    "ground_truth": {
        "vulnerable_indices": [0, 2, 4],
        "safe_indices": [1, 3],
        "vulnerabilities": {
            0: {"type": "sql_injection", "severity": "critical", "pattern": "string_concatenation"},
            2: {"type": "sql_injection", "severity": "critical", "pattern": "union_attack"},
            4: {"type": "sql_injection", "severity": "critical", "pattern": "dynamic_sql"},
        }
    }
}

# ─── TASK MEDIUM ───────────────────────────────────────────────────────────────

TASK_MEDIUM = {
    "id": "task_medium",
    "name": "Query Performance Optimizer (Medium)",
    "difficulty": "medium",
    "max_steps": 30,
    "phase_sequence": ["scanning", "optimizing"],
    "queries": [
        # 0: N+1 pattern - should use JOIN
        "SELECT * FROM orders WHERE user_id = (SELECT id FROM users WHERE email = 'john@example.com')",
        # 1: SELECT * on large table - missing column pruning
        "SELECT * FROM order_items WHERE order_id = 12345",
        # 2: Missing index on high-cardinality filter
        "SELECT * FROM orders WHERE total_amount > 1000 AND status = 'pending'",
        # 3: Cartesian join (no join condition)
        "SELECT u.email, o.total_amount FROM users u, orders o WHERE o.total_amount > 500",
        # 4: Good query - uses index, minimal columns
        "SELECT o.id, o.total_amount, o.created_at FROM orders o WHERE o.user_id = %s AND o.status = 'completed' ORDER BY o.created_at DESC LIMIT 20",
        # 5: Function on indexed column kills index usage
        "SELECT * FROM orders WHERE YEAR(created_at) = 2024 AND MONTH(created_at) = 1",
        # 6: Missing LIMIT on full-table scan
        "SELECT id, email, full_name, ssn FROM users ORDER BY created_at DESC",
        # 7: Redundant subquery pattern
        "SELECT * FROM products WHERE id IN (SELECT product_id FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = 42))"
    ],
    "ground_truth": {
        "performance_issues": {
            0: {"issue": "subquery_can_be_join", "severity": "high", "fix": "JOIN"},
            1: {"issue": "select_star", "severity": "medium", "fix": "explicit_columns"},
            2: {"issue": "missing_composite_index", "severity": "high", "fix": "add_index"},
            3: {"issue": "cartesian_join", "severity": "critical", "fix": "explicit_join_condition"},
            5: {"issue": "function_on_indexed_column", "severity": "high", "fix": "range_predicate"},
            6: {"issue": "missing_limit", "severity": "high", "fix": "add_limit"},
            7: {"issue": "nested_subqueries", "severity": "medium", "fix": "join_chain"},
        },
        "clean_queries": [4],
        "rewrite_hints": {
            3: "Add explicit JOIN ... ON condition",
            5: "Use created_at BETWEEN '2024-01-01' AND '2024-01-31' to leverage index",
            7: "Rewrite as JOIN chain or use CTEs",
        }
    }
}

# ─── TASK HARD ─────────────────────────────────────────────────────────────────

TASK_HARD = {
    "id": "task_hard",
    "name": "Full Audit Pipeline (Hard)",
    "difficulty": "hard",
    "max_steps": 50,
    "phase_sequence": ["scanning", "optimizing", "compliance", "reporting"],
    "queries": [
        # 0: Injection + exposes PII
        "SELECT id, email, ssn, password_hash FROM users WHERE username = '" + "' + input",
        # 1: Exposes PII - GDPR concern, no business need
        "SELECT u.full_name, u.ssn, u.email, u.password_hash, o.total_amount FROM users u JOIN orders o ON u.id = o.user_id",
        # 2: Cartesian join + PII exposure
        "SELECT * FROM users, audit_logs",
        # 3: Performance issue - function on indexed column
        "SELECT * FROM audit_logs WHERE DATE(created_at) = CURDATE()",
        # 4: Injection via dynamic table name
        "SET @sql = CONCAT('SELECT * FROM ', @table_name); PREPARE stmt FROM @sql; EXECUTE stmt;",
        # 5: GDPR violation - logs ip_address without retention check
        "INSERT INTO audit_logs (user_id, action, ip_address, created_at) SELECT id, 'export', ip_address, NOW() FROM users",
        # 6: Password hash leakage to API layer
        "SELECT id, email, password_hash, role FROM users WHERE email = %s",
        # 7: Missing LIMIT on admin endpoint
        "SELECT u.id, u.email, u.full_name, u.ssn, u.role FROM users u WHERE u.role != 'deleted' ORDER BY u.created_at DESC",
        # 8: Clean query
        "SELECT id, status, total_amount, created_at FROM orders WHERE user_id = %s AND status = %s ORDER BY created_at DESC LIMIT 10",
        # 9: N+1 subquery
        "SELECT p.name, p.price FROM products p WHERE p.id IN (SELECT product_id FROM order_items WHERE order_id = 999)",
        # 10: Truncation risk + no WHERE clause
        "UPDATE users SET role = 'admin'",
        # 11: Missing transaction + data integrity
        "INSERT INTO orders (user_id, status, total_amount) VALUES (%s, 'pending', %s); UPDATE users SET last_order_at = NOW() WHERE id = %s",
    ],
    "ground_truth": {
        "security_issues": {0: "critical", 4: "critical", 10: "critical"},
        "pii_exposure": {0: True, 1: True, 2: True, 6: True, 7: True},
        "performance_issues": {2: "cartesian", 3: "function_on_index", 7: "missing_limit", 9: "n+1", 11: "missing_transaction"},
        "compliance_flags": {1: "gdpr_pii_overexposure", 5: "gdpr_ip_retention", 6: "password_leakage", 7: "gdpr_pii_overexposure"},
        "clean_queries": [8],
        "required_report_sections": ["executive_summary", "critical_findings", "compliance_violations", "recommendations"],
        "min_critical_findings": 3,
        "min_compliance_flags": 2,
    }
}

TASKS: Dict[str, Any] = {
    "task_easy": TASK_EASY,
    "task_medium": TASK_MEDIUM,
    "task_hard": TASK_HARD,
}
