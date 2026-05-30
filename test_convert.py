import wave
import struct
import requests
import os

# create 1s silent wav
fname = 'test_silence.wav'
framerate = 44100
duration = 1
nframes = framerate * duration
with wave.open(fname, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(framerate)
    frames = b''
    for i in range(nframes):
        frames += struct.pack('<h', 0)
    wf.writeframes(frames)

print('Created', fname)

url = 'http://127.0.0.1:5000/api/convert'
files = {'file': (fname, open(fname, 'rb'), 'audio/wav')}
data = {'format': 'mp3'}
print('Uploading to', url)
resp = requests.post(url, files=files, data=data, stream=True)

if resp.status_code == 200:
    out = 'converted_test.mp3'
    with open(out, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print('Saved converted file to', out)
else:
    try:
        print('Error:', resp.json())
    except Exception:
        print('HTTP', resp.status_code)

# cleanup sample wav
try:
    os.remove(fname)
except:
    pass
