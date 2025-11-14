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
        xterm \
        git \
        libglib2.0-dev \
        libfdt-dev \
        libpixman-1-dev \
        zlib1g-dev \
        ninja-build \
        libsdl2-dev \
        libgtk-3-dev \
        qemu-system-i386 \
        qemu-system-gui \
        qemu-utils \
        tesseract-ocr \
        git \
        vim \
        python3-venv \
        mtools 

RUN apt-get build-dep -y qemu-system-misc ninja || true
RUN apt-get remove -y light-locker xscreensaver
RUN apt-get autoremove -y
RUN rm -rf /var/cache/apt /var/lib/apt/lists/*

# Install Firefox manually
#RUN wget -O /tmp/firefox.tar.bz2 "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" --no-check-certificate && \
#    tar xvf /tmp/firefox.tar.bz2 -C /opt && \
#    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
#    rm /tmp/firefox.tar.bz2

# Fix XRDP/X11 setup
RUN mkdir -p /var/run/dbus && \
    cp /etc/X11/xrdp/xorg.conf /etc/X11 || true && \
    sed -i "s/console/anybody/g" /etc/X11/Xwrapper.config && \
    sed -i "s|xrdp/xorg|xorg|g" /etc/xrdp/sesman.ini && \
    echo "xfce4-session" >> /etc/skel/.Xsession

ENV VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

WORKDIR /root

# build m68k from src
RUN git clone https://gitlab.com/qemu-project/qemu.git && \
cd qemu && \
./configure --target-list=m68k-softmmu --enable-gtk --enable-sdl --enable-slirp && \
make -j4


COPY requirements.txt /app/
# create venv
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r /app/requirements.txt && \
    chgrp -R users /opt/venv && \
    chmod -R g+rwX /opt/venv && \
    find /opt/venv -type d -exec chmod g+s {} \;
ENV VENV_PATH=/opt/venv


COPY entrypoint.sh /app
RUN chmod +x /app/entrypoint.sh

EXPOSE 3389 8080
ENTRYPOINT ["/app/entrypoint.sh"]