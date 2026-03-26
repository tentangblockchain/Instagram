module.exports = {
  apps: [
    {
      name: "telegram-bot",

      // Jalankan sebagai modul Python
      script: "python3",
      args: "-m bot.main",
      interpreter: "none",

      // Working directory (sesuaikan dengan path project kamu)
      cwd: "./",

      // Jangan restart jika exit bersih (kode 0)
      stop_exit_codes: [0],

      // Restart otomatis jika crash
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 5000,

      // Environment variables
      // Pastikan file .env sudah diisi sebelum start
      env: {
        NODE_ENV: "production",
      },

      // Log
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      out_file: "./logs/bot-out.log",
      error_file: "./logs/bot-error.log",
      merge_logs: false,
      log_type: "json",

      // Rotate log agar tidak membengkak
      // Butuh: pm2 install pm2-logrotate
      max_size: "10M",
      retain: 7,

      // Jika memory lebih dari 512MB, restart otomatis
      max_memory_restart: "512M",

      // Monitoring
      watch: false,
    },
  ],
};
