module.exports = {
  testDir: "tests/e2e",
  use: {
    baseURL: process.env.ARGUS_TEST_URL || "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command:
      (process.platform === "win32" ? ".\\.venv313\\Scripts\\python.exe" : "python") +
      " manage.py runserver 127.0.0.1:8000 --noreload",
    url: "http://127.0.0.1:8000/health/",
    reuseExistingServer: true,
  },
  reporter: "list",
};
