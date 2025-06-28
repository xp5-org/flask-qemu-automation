FROM ubuntu:25.04
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Update and install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        xfce4 \
        xfce4-clipman-plugin \
        xfce4-cpugraph-plugin \
        xfce4-netload-plugin \
        xserver-xorg-legacy \
        xdg-utils \
        dbus-x11 \
        xfce4-screenshooter \
        xfce4-taskmanager \
        xfce4-terminal \
        xfce4-xkb-plugin \
        xorgxrdp \
        xrdp \
        sudo \
        wget \
        bzip2 \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        # xterm for runme.sh debug
        xterm \
        qemu-system-i386 \
        qemu-system-gui \
        qemu-utils \
        tesseract-ocr \
        git \
        vim \
        python3-venv \
        mtools && \
    apt-get remove -y light-locker xscreensaver && \
    apt-get autoremove -y && \
    rm -rf /var/cache/apt /var/lib/apt/lists/*

# Install Firefox manually
RUN wget -O /tmp/firefox.tar.bz2 "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" --no-check-certificate && \
    tar xvf /tmp/firefox.tar.bz2 -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.bz2

# Fix XRDP/X11 setup
RUN mkdir -p /var/run/dbus && \
    cp /etc/X11/xrdp/xorg.conf /etc/X11 || true && \
    sed -i "s/console/anybody/g" /etc/X11/Xwrapper.config && \
    sed -i "s|xrdp/xorg|xorg|g" /etc/xrdp/sesman.ini && \
    echo "xfce4-session" >> /etc/skel/.Xsession

ENV VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

WORKDIR /app

RUN git clone https://github.com/xp5-org/flask-qemu-automation.git /app

# Create the virtual environment and install dependencies
RUN python3 -m venv $VENV_PATH && \
    $VENV_PATH/bin/pip install --upgrade pip && \
    $VENV_PATH/bin/pip install -r requirements.txt


COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 3389 8080
ENTRYPOINT ["/app/entrypoint.sh"]
