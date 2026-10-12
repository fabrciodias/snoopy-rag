const fs = require("node:fs");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");

const pythonCandidates = [
  // Ambientes virtuais comuns no Linux.
  path.join(projectRoot, "venv", "bin", "python"),
  path.join(projectRoot, "venv", "bin", "python3"),
  path.join(projectRoot, ".venv", "bin", "python"),
  path.join(projectRoot, ".venv", "bin", "python3"),

  // Ambientes virtuais comuns no Windows.
  path.join(projectRoot, "venv", "Scripts", "python.exe"),
  path.join(projectRoot, ".venv", "Scripts", "python.exe")
];

const pythonPath = pythonCandidates.find((candidate) =>
  fs.existsSync(candidate)
);

if (!pythonPath) {
  throw new Error(
    "Não foi encontrado um ambiente virtual Python. " +
    "Crie o ambiente virtual na raiz do projeto, usando " +
    "o diretório 'venv' ou '.venv', e instale as dependências."
  );
}

module.exports = {
  apps: [
    {
      name: "snoopy-rag-v3",

      script: pythonPath,
      interpreter: "none",

      args: [
        "-m",
        "uvicorn",
        "backend.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "3000"
      ],

      cwd: projectRoot,

      instances: 1,
      exec_mode: "fork",

      autorestart: true,
      watch: false,

      min_uptime: "10s",
      max_restarts: 10,
      restart_delay: 3000,
      kill_timeout: 10000,

      time: true,

      env_production: {
        ENVIRONMENT: "production",
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};