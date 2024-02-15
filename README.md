# Wyoming Porcupine3

[Wyoming protocol](https://github.com/rhasspy/wyoming) server for the [porcupine3](https://github.com/Picovoice/porcupine) wake word detection system.

# Local Install

Clone the repository and set up Python virtual environment:

```bash
git clone https://github.com/piitaya/wyoming-porcupine3.git
cd wyoming-porcupine3
script/setup
```

Run a server that anyone can connect to:

```bash
script/run --uri 'tcp://0.0.0.0:10400'
```

## Docker Image

```sh
docker run -it -p 10400:10400 piitaya/wyoming-porcupine3
```
