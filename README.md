# signal-scanner-bot
This bot monitors the DSA's Scanner signal channel and forwards relevant police comm messages to our twitter account.

The bot uses the [signal-cli](https://github.com/AsamK/signal-cli) library to listen to signal on a dedicated device number.
The number must be registered to the container running the bot.
Configuration information is stored in `$XDG_DATA_HOME/signal-cli`, so `$XDG_DATA_HOME` is mounted as a volume in the `docker-compose.yml` file to preserve configuration across startups.

Twitter credentials and Signal config is defined via environment variables.
To deploy, copy `.env.example` to `.env` and populate with the appropriate values.


## Setup

A phone must be registered prior to running the container.
This can be done with the following command:
```bash
docker-compose run --rm cli ./register-number.sh
```

After following the registration prompts with your device, the container can be run with:
```bash
docker-compose up -d
```
