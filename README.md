# signal-scanner-bot
This bot monitors the DSA's Scanner signal channel and forwards relevant police comm messages to our twitter account.

The bot uses the [signal-cli](https://github.com/AsamK/signal-cli) library to listen to signal on a dedicated device number.
The number must be registered to the container running the bot.
Configuration information is stored in `$XDG_DATA_HOME/signal-cli`, so `$XDG_DATA_HOME` is mounted as a volume in the `docker-compose.yml` file to preserve configuration across startups.

Twitter credentials and Signal config is defined via environment variables.
To deploy, copy `.env.example` to `.env` and populate with the appropriate values.


## Setup

### Prerequisites

Before getting started, you will have to set up a few things first:

1. Install [Docker](https://www.docker.com/products/docker-desktop).
2. Install [`just`](https://github.com/casey/just).
3. Install [Signal](https://signal.org/en/download/) on your phone
4. Copy `.env.example` to `.env` and populate with the appropriate values.
5. Create a [Google Voice](https://voice.google.com) number.
6. Create a Signal account with the Google Voice number from the previous step.
7. Create a [Twitter Developer Account](https://developer.twitter.com/en/apply-for-access) if you don't have one.
8. Generate API Keys and Access Tokens on the Twitter Developer portal. You will be using them in the `.env` file later.

### Using `just`

We use `just` as our command runner for this repo.
The same `just` commands described below can be used to deploy production.
The `docker-compose-prod.yml` file defines the minimum services for running in production.
In order to use this file, set the `IS_PROD` environment variable to `true`.
This will run all commands using the prod docker file.

A phone must be registered prior to running the container.
This can be done with the following command:
```bash
just register
```

After following the registration prompts with your device, the container can be run with:
```bash
just up
```

If a safety number in a group changes, the signal-cli will have issues sending messages.
The following verification utility will re-verify these numbers.
```bash
just verify
```

### Setting up the environment

Before setting up your environment, please ensure that you have all the prerequisite steps above fulfilled.

To get started, populate the `.env` file with your information, such as your Google Voice number and Twitter tokens. For example:

```bash
BOT_NUMBER=<Google Voice number>
ADMIN_CONTACT=<Your number>
TWITTER_API_KEY=<Generated Twitter API Key>
TWITTER_API_SECRET=<Generated Twitter API Secret>
TWITTER_ACCESS_TOKEN=<Generated Twitter Access Token>
TWITTER_TOKEN_SECRET=<Generated Twitter Access Token Secret>
...

```

Note that to you do not need to fill out all of the environment variables yet. Many of these variables will have defaults. To use the defaults, simply remove the variable line. For example, if you would like to use the default timezone, you would remove the entire line:

`DEFAULT_TZ=TZ database formatted name for a timezone. Defaults to US/Pacific`

Once you have your phone numbers in the `.env` file, run `just register`.

**WINDOWS USERS:** If you are on Windows, you can pass this into your `justfile` to allow it to use Powershell instead of using `sh`:

```
# use PowerShell instead of sh:
set shell := ["powershell.exe", "-c"]
```

When running `just register`, it should prompt you to receive a CAPTCHA token:

```bash
> just register
docker-compose --file=docker-compose.yml --file=docker-compose.override.yml run --rm cli ./register-number.sh
Creating signal-scanner-bot_cli_run ... done
Captcha required, please visit https://signalcaptchas.org/registration/generate.html to receive a captcha token
```

**Note:** If you do not get this response, double check your environment variables in the `.env` file.

Visit the link provided in the response, which will prompt you to open Signal. You should be greeted with a blank webpage. You can close out of the prompt, as you do not require the client to be running to verify the CAPTCHA.

On the blank webpage, run the inspect tool for your browser. In the Console logs, you should see a message like such:

`>Launched external handler for 'signalcaptcha://<string>'.`

See below screenshot for more details. Note that the entire string is highlighted, and that the generate.html:1 is not part of the string but an artifact of how the logger in the console looks.
<img width="674" alt="Screen Shot 2021-11-24 at 9 14 05 PM" src="https://user-images.githubusercontent.com/13648427/143383579-b6b9e12a-b8cf-4c28-b509-ea4740cb3ff2.png">

Copy the entire string that comes after `signalcaptcha://`. This will be the code you use to verify the CAPTCHA in your terminal. It should be a 484 character-long string.

For more information on this step, you can check out this page here: [Registration with captcha](https://github.com/AsamK/signal-cli/wiki/Registration-with-captcha)

Once successful, you will be asked to enter the verification value sent to your primary phone. This will be sent to the Google Voice number that you set as a value for the environment variable `BOT_NUMBER`.

If the verification code is accepted, you will receive a return message stating that verification was successful, and that the Google Voice number can now be used:

`>Verification succeeded, +<BOT_NUMBER> can now be used`

Next, run `just up` to run your container. 

To verify that everything is working, you can run `docker logs $(docker ps | grep "sdsa/signal-scanner-bot" | awk -F ' ' '{print $1}')` to see the logs.

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

For Windows users using VSC, make sure that the **End of Line Sequence** is selected to be `LF` on the script `/scripts/register-number.sh`. If `CRLF` is selected, you will run into an error:

`standard_init_linux.go:228: exec user process caused: no such file or directory`