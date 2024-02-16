# Wyoming Porcupine3

[Wyoming protocol](https://github.com/rhasspy/wyoming) server for the [porcupine3](https://github.com/Picovoice/porcupine) wake word detection system.

You need a Picovoice access key to run Porcupine 3.

# Local Install

Clone the repository and set up Python virtual environment:

```bash
git clone https://github.com/piitaya/wyoming-porcupine3.git
cd wyoming-porcupine3
script/setup
```

Run a server that anyone can connect to:

```bash
script/run --uri 'tcp://0.0.0.0:10400' --access-key='PICOVOICE_ACCESS_KEY'
```

## Docker Image

Docker is not supported for now because of access key limitation (more info here: https://github.com/Picovoice/picovoice/issues/552).
