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

If a safety number in a group changes, the signal-cli will have issues sending messages.
The following verification utility will re-verify these numbers.
```bash
docker-compose run --rm cli signal-scanner-bot-verify
```

## Technicalities

The app has two primary loops, the Signal-to-Twitter loop and the Twitter-to-Signal loop.
The loop is constrained by the limitation that only one instance of `signal-cli` can be running at once.
While `signal-cli` has its own lock, this is mitigated a bit more by a python-level lock.

### Signal-to-Twitter
This loop runs the `receive` command on the `signal-cli` for `env.SIGNAL_TIMEOUT` seconds, parsing messages as they arrive.
The messages are passed through a series of filters to see if they match the desired criteria.
If they do, the text of the message gets timestamped and Tweeted out with a pre-defined set of hashtags.

### Twitter-to-Signal
This loop uses `tweepy`'s streaming API to "track" certain hashtags.
Similar to the S2T loop, messages pass through filters to see if the criteria is met.
If it is, the `signal-cli` lock is acquired and the contents of the Tweet is sent to the desired Signal group.

### Hierarchy

* The `env` module supplies environment information/secrets to all loops.
* The `filter` module is used to define message filters for both Signal & Twitter.
* The `signal` and `twitter` modules compose the basic building blocks of sending/reading to each platform.
* The `messages` module combines both Signal & Twitter functionality into higher level `process_*` functions.
* Lastly, the `transport` module defines the primary read/send loops, using the process functions defined in `messages`.

### Issues
Both of these loops use `ascynio` to run concurrently, but as stated above they share the `signal-cli` lock
Already I've noticed some issues with this setup that I'm hoping to address in the future:
* T2S messages take a long time to actually get sent
* Even with the lock, the CLI in the T2S loop still complains that signal is in use and the CLI lock requires some time to be acquired
