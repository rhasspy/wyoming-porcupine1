# Wyoming Porcupine3

[Wyoming protocol](https://github.com/rhasspy/wyoming) server for the [porcupine3](https://github.com/Picovoice/porcupine) wake word detection system.

You need a Picovoice access key to run Porcupine 3. you can create a free account on the (Picovoice website)[https://picovoice.ai/]

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

## Custom Models

You can train up to 3 wake words per month for free using the [picovoice console](https://console.picovoice.ai/ppn). Create a folder (e.g. `custom_wake_words`), put your wake word files (`.ppn`) inside the folder and run the following command.

```bash
script/run --uri 'tcp://0.0.0.0:10400' --access-key='PICOVOICE_ACCESS_KEY' --custom-wake-words-dir='custom_wake_words'
```

## Docker Image

Docker is not supported for now because of access key limitation (more info here: https://github.com/Picovoice/picovoice/issues/552).
