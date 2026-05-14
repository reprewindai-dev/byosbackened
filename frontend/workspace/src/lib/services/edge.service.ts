import { api } from "@/lib/api";

export const edgeService = {
  // ─── Edge Ingest ─────────────────────────────────────────
  /** POST /edge/ingest */
  ingest: (body: Record<string, unknown>) => api.post("/edge/ingest", body),

  /** POST /edge/ingest/batch */
  batchIngest: (items: Record<string, unknown>[]) =>
    api.post("/edge/ingest/batch", { items }),

  // ─── Edge Control ────────────────────────────────────────
  /** GET /edge/devices */
  listDevices: (params?: { page?: number; limit?: number; status?: string }) =>
    api.get("/edge/devices", { params }),

  /** GET /edge/devices/{device_id} */
  getDevice: (device_id: string) => api.get(`/edge/devices/${device_id}`),

  /** POST /edge/devices/{device_id}/command */
  sendCommand: (device_id: string, body: { command: string; params?: Record<string, unknown> }) =>
    api.post(`/edge/devices/${device_id}/command`, body),

  /** GET /edge/devices/{device_id}/telemetry */
  getDeviceTelemetry: (device_id: string, params?: { from?: string; to?: string }) =>
    api.get(`/edge/devices/${device_id}/telemetry`, { params }),

  // ─── MQTT ────────────────────────────────────────────────
  /** POST /edge/mqtt/publish */
  mqttPublish: (body: { topic: string; payload: unknown; qos?: number }) =>
    api.post("/edge/mqtt/publish", body),

  /** POST /edge/mqtt/subscribe */
  mqttSubscribe: (body: { topics: string[] }) =>
    api.post("/edge/mqtt/subscribe", body),

  // ─── Modbus ──────────────────────────────────────────────
  /** POST /edge/modbus/read */
  modbusRead: (body: { device_id: string; register: number; count?: number }) =>
    api.post("/edge/modbus/read", body),

  /** POST /edge/modbus/write */
  modbusWrite: (body: { device_id: string; register: number; value: number }) =>
    api.post("/edge/modbus/write", body),

  // ─── SNMP ────────────────────────────────────────────────
  /** POST /edge/snmp/get */
  snmpGet: (body: { host: string; oid: string; community?: string }) =>
    api.post("/edge/snmp/get", body),

  /** POST /edge/snmp/walk */
  snmpWalk: (body: { host: string; oid: string; community?: string }) =>
    api.post("/edge/snmp/walk", body),

  // ─── Edge Canary ─────────────────────────────────────────
  /** GET /edge/canary/status */
  getCanaryStatus: () => api.get("/edge/canary/status"),

  /** POST /edge/canary/ping */
  canaryPing: (body?: Record<string, unknown>) =>
    api.post("/edge/canary/ping", body),
};
