const path = require("path");

// ==========================================
// WINDOWS PM2 CONFIGURATION
// Python virtual environment interpreter path:
// .venv\Scripts\python.exe
// ==========================================
const pythonInterpreter = path.resolve(__dirname, ".venv", "Scripts", "python.exe");

module.exports = {
  apps: [
    {
      name: "jobseeker-gateway",
      cwd: __dirname,
      script: "run_jobseeker.py",
      interpreter: pythonInterpreter,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      }
    },

    {
      name: "company-gateway",
      cwd: __dirname,
      script: "run_company.py",
      interpreter: pythonInterpreter,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      }
    },

    {
      name: "superadmin-gateway",
      cwd: __dirname,
      script: "run_admin.py",
      interpreter: pythonInterpreter,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
