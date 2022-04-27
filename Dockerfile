FROM openjdk:17-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    SIGNAL_CLI_VERSION=0.10.5

# Install OpenJDK-8
RUN apt-get update && \
    apt-get install -y \
        python3.9 \
        python3.9-dev \
        python3-pip \
        wget \
        openjdk-17-jdk-headless \
        openjdk-17-jre-headless \
        ca-certificates-java \
        dos2unix && \
    rm -rf /var/lib/apt/lists/* && \
    update-ca-certificates -f

# Install signal-cli
WORKDIR /tmp
RUN wget -q https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/signal-cli-${SIGNAL_CLI_VERSION}-Linux.tar.gz && \
    tar xf /tmp/signal-cli-${SIGNAL_CLI_VERSION}-Linux.tar.gz -C /opt && \
    ln -sf /opt/signal-cli-${SIGNAL_CLI_VERSION}/bin/signal-cli /usr/local/bin/

WORKDIR /app
COPY scripts/register-number.sh .
RUN dos2unix ./register-number.sh
COPY . .
RUN pip install -r requirements.txt && pip install -e .

CMD ["signal-scanner-bot"]
