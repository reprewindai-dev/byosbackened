import subprocess, re
result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
for line in result.stdout.splitlines():
    if ":8765" in line and "LISTENING" in line:
        pid = line.strip().split()[-1]
        if pid.isdigit():
            print(f"Killing PID {pid}")
            subprocess.run(["taskkill", "/F", "/PID", pid])
