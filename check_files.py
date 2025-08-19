import requests
import json

# Get files from tracks API
response = requests.get('http://localhost:8000/api/tracks/?limit=10')
data = response.json()

print(f"Total files: {data['total_count']}")

print("\nFile statuses:")
for f in data['tracks']:
    print(f"{f['file_name']}: {f['analysis_status']} (essentia: {f['essentia_analyzed']}, tensorflow: {f['tensorflow_analyzed']}, faiss: {f['faiss_analyzed']})")

# Group files by analysis_status
status_counts = {}
for f in data['tracks']:
    status = f['analysis_status']
    if status not in status_counts:
        status_counts[status] = []
    status_counts[status].append(f['file_name'])

print("\nFiles by status:")
for status, files in status_counts.items():
    print(f"{status}: {len(files)} files")
    if len(files) <= 3:
        for file in files:
            print(f"  - {file}")
    else:
        print(f"  - {files[0]}")
        print(f"  - {files[1]}")
        print(f"  - ... and {len(files)-2} more")
