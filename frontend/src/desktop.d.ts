export {};

declare global {
  interface Window {
    crpsDesktop?: {
      getVersion: () => Promise<string>;
      getMachineInfo: () => Promise<{
        hostname: string;
        platform: string;
        arch: string;
        ip_address?: string;
        timezone?: string;
      }>;
      getSystemMetrics: () => Promise<{ cpu_usage: number; ram_usage: number }>;
    };
  }
}
