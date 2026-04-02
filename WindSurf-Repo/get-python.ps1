# Download and extract portable Python 3.11
$pythonZip = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-embed-amd64.zip"
$dest = "C:\Python311"

# Download
Invoke-WebRequest -Uri $pythonZip -OutFile "$env:TEMP\python311.zip"

# Extract
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Path $dest -Force
Expand-Archive -Path "$env:TEMP\python311.zip" -DestinationPath $dest

# Verify
& "$dest\python.exe" --version
