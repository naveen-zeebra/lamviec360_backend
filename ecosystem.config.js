module.exports = {
  apps: [
    {
      name: "jobseeker-gateway",
      script: "run_jobseeker.py",
      interpreter: "python",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
      },
    },
    {
      name: "company-gateway",
      script: "run_company.py",
      interpreter: "python",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
      },
    },
    {
      name: "superadmin-gateway",
      script: "run_admin.py",
      interpreter: "python",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
