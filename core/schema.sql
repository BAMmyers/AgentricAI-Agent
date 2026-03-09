-- Create database if not exists
CREATE DATABASE IF NOT EXISTS agentricai;

-- Connect to the database
ATTACH DATABASE 'agentricai.db' AS db;

-- Create table for agent identity
CREATE TABLE IF NOT EXISTS agents (
    UID TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create table for capabilities
CREATE TABLE IF NOT EXISTS capabilities (
    agent_UID TEXT,
    capability_name TEXT,
    description TEXT,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for tools
CREATE TABLE IF NOT EXISTS tools (
    tool_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_UID TEXT,
    tool_name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for adapters
CREATE TABLE IF NOT EXISTS adapters (
    adapter_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_ID INTEGER,
    adapter_type TEXT NOT NULL,
    configuration TEXT,
    FOREIGN KEY (tool_ID) REFERENCES tools(tool_ID)
);

-- Create table for memory modes
CREATE TABLE IF NOT EXISTS memory_modes (
    mode_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_UID TEXT,
    mode_name TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for provenance
CREATE TABLE IF NOT EXISTS provenance (
    log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_UID TEXT,
    action TEXT NOT NULL,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_UID TEXT,
    user_action TEXT NOT NULL,
    user_details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for lifecycle state
CREATE TABLE IF NOT EXISTS lifecycle_state (
    state_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_UID TEXT,
    state_name TEXT NOT NULL,
    description TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_UID) REFERENCES agents(UID)
);

-- Create table for MCP tool references
CREATE TABLE IF NOT EXISTS mcp_tools (
    tool_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (tool_ID) REFERENCES tools(tool_ID)
);

-- Create table for environment bindings
CREATE TABLE IF NOT EXISTS environment_bindings (
    binding_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_ID INTEGER,
    environment_type TEXT NOT NULL,
    configuration TEXT,
    FOREIGN KEY (tool_ID) REFERENCES mcp_tools(tool_ID)
);

-- Initialize data if needed
INSERT INTO agents (UID, name, domain, version) VALUES ('12345678-1234-1234-1234-1234567890ab', 'Agent1', 'DomainA', '1.0.0');

INSERT INTO capabilities (agent_UID, capability_name, description) VALUES ('12345678-1234-1234-1234-1234567890ab', 'Task1', 'Capability to perform task 1');
INSERT INTO tools (tool_ID, agent_UID, tool_name, version, description) VALUES (1, '12345678-1234-1234-1234-1234567890ab', 'ToolA', '1.0.0', 'Tool for task 1');
INSERT INTO adapters (adapter_ID, tool_ID, adapter_type, configuration) VALUES (1, 1, 'TypeA', '{"config": "value"}');
INSERT INTO memory_modes (mode_ID, agent_UID, mode_name, description) VALUES (1, '12345678-1234-1234-1234-1234567890ab', 'ModeA', 'Memory mode A');
INSERT INTO provenance (log_ID, agent_UID, action, details) VALUES (1, '12345678-1234-1234-1234-1234567890ab', 'Action1', '{"details": "Performed action 1"}');
INSERT INTO audit_logs (log_ID, agent_UID, user_action, user_details) VALUES (1, '12345678-1234-1234-1234-1234567890ab', 'UserAction1', '{"details": "User performed action 1"}');
INSERT INTO lifecycle_state (state_ID, agent_UID, state_name, description) VALUES (1, '12345678-1234-1234-1234-1234567890ab', 'StateA', 'Lifecycle state A');
INSERT INTO mcp_tools (tool_ID, tool_name, version, description) VALUES (1, 'MCPToolA', '1.0.0', 'MCP tool for task 1');
INSERT INTO environment_bindings (binding_ID, tool_ID, environment_type, configuration) VALUES (1, 1, 'TypeB', '{"config": "value"}');

-- Detach the database
DETACH DATABASE db;