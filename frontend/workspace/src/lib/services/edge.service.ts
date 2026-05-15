import { api, noRoute } from "@/lib/api";

export const edgeService = {
  // ─── Edge Ingest ─────────────────────────────────────────
  /** POST /edge/ingest */
  ingest: (body: Record<string, unknown>) => api.post("/edge/ingest", body),

  /** POST /edge/ingest/batch */
  batchIngest: (items: Record<string, unknown>[]) =>
    noRoute("/edge/ingest/batch", items),

  // ─── Edge Control ────────────────────────────────────────
  /** GET /edge/devices */
  listDevices: (params?: { page?: number; limit?: number; status?: string }) =>
    noRoute("/edge/devices", params),

  /** GET /edge/devices/{device_id} */
  getDevice: (device_id: string) => noRoute(`/edge/devices/${device_id}`),

  /** POST /edge/devices/{device_id}/command */
  sendCommand: (device_id: string, body: { command: string; params?: Record<string, unknown> }) =>
    noRoute(`/edge/devices/${device_id}/command`, body),

  /** GET /edge/devices/{device_id}/telemetry */
  getDeviceTelemetry: (device_id: string, params?: { from?: string; to?: string }) =>
    noRoute(`/edge/devices/${device_id}/telemetry`, params),

  // ─── MQTT ────────────────────────────────────────────────
  /** POST /edge/mqtt/publish */
  mqttPublish: (body: { topic: string; payload: unknown; qos?: number }) =>
    noRoute("/edge/mqtt/publish", body),

  /** POST /edge/mqtt/subscribe */
  mqttSubscribe: (body: { topics: string[] }) =>
    noRoute("/edge/mqtt/subscribe", body),

  // ─── Modbus ──────────────────────────────────────────────
  /** POST /edge/modbus/read */
  modbusRead: (body: { device_id: string; register: number; count?: number }) =>
    noRoute("/edge/modbus/read", body),

  /** POST /edge/modbus/write */
  modbusWrite: (body: { device_id: string; register: number; value: number }) =>
    noRoute("/edge/modbus/write", body),

  // ─── SNMP ────────────────────────────────────────────────
  /** POST /edge/snmp/get */
  snmpGet: (body: { host: string; oid: string; community?: string }) =>
    noRoute("/edge/snmp/get", body),

  /** POST /edge/snmp/walk */
  snmpWalk: (body: { host: string; oid: string; community?: string }) =>
    noRoute("/edge/snmp/walk", body),

  // ─── Edge Canary ─────────────────────────────────────────
  /** GET /edge/canary/status */
  getCanaryStatus: () => api.get("/edge/canary/public"),

  /** POST /edge/canary/ping */
  canaryPing: (body?: Record<string, unknown>) =>
    api.post("/admin/edge/canary/run", body),
};
