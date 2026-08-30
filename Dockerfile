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
        xvfb \
        openssh-server \
        sudo \
        wget \
        curl \
        bzip2 \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        xterm \
        git \
        patchelf \
        # QEMU build deps. QEMU itself is built from source further down
        libglib2.0-dev \
        libfdt-dev \
        libpixman-1-dev \
        zlib1g-dev \
        ninja-build \
        libsdl2-dev \
        libgtk-3-dev \
        libslirp-dev \
        simh \
        verilator \
        dosbox-x \
        tesseract-ocr \
        git \
        vim \
        python3-venv \
        mtools \
        xdotool \
        imagemagick \
        # for pipewire
        pipewire \
        pipewire-pulse wireplumber \
        pipewire-audio-client-libraries \
        dbus-user-session alsa-utils \
        pipewire-module-xrdp \
        pulseaudio-utils \
        autoconf \
        automake \
        libtool \
        pkg-config \
        libpipewire-0.3-dev \
        libspa-0.2-dev \
        cmake \
        bison \
        flex \
        texinfo \
        libgmp-dev \
        libmpfr-dev \
        libmpc-dev \
        libboost-all-dev \
        # ruby needed for make-multiverse.rb
        ruby
RUN apt-get build-dep -y qemu-system-misc ninja || true
RUN apt-get remove -y light-locker xscreensaver
RUN apt-get autoremove -y
RUN rm -rf /var/cache/apt /var/lib/apt/lists/*

# get the good tesseract ocr data
RUN mkdir -p /usr/local/share/tessdata && \
    curl -sL -o /usr/local/share/tessdata/eng.traineddata \
        https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata

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


# build latest QEMU from src
ARG QEMU_VERSION=latest
WORKDIR /tmp
RUN set -eux; \
    if [ "$QEMU_VERSION" = "latest" ]; then \
        QEMU_VERSION="$(git ls-remote --tags --refs https://github.com/qemu/qemu.git \
            | sed -n 's|.*refs/tags/\(v[0-9]*\.[0-9]*\.[0-9]*\)$|\1|p' \
            | sort -V | tail -1)"; \
    fi; \
    echo "Building QEMU $QEMU_VERSION"; \
    git clone --depth 1 --branch "$QEMU_VERSION" \
        https://github.com/qemu/qemu.git /tmp/qemu; \
    cd /tmp/qemu; \
    ./configure \
        --target-list=i386-softmmu,m68k-softmmu,ppc-softmmu,sparc-softmmu \
        --enable-gtk --enable-sdl --enable-slirp --enable-tools --disable-docs; \
    make -j"$(nproc)"; \
    make install; \
    cd /; rm -rf /tmp/qemu; \
    qemu-system-i386 --version | head -1

# retro68 installs to /opt/Retro68/toolchain
WORKDIR /opt
RUN git clone --recursive https://github.com/autc04/Retro68.git /opt/Retro68 && \
    mkdir -p /opt/Retro68-build && \
    cd /opt/Retro68-build && \
    /opt/Retro68/build-toolchain.bash --no-ppc --no-carbon \
        --prefix=/opt/Retro68/toolchain --clean-after-build && \
    rm -rf /opt/Retro68-build

# 86Box
WORKDIR /opt
RUN curl -sL -o /tmp/86box.AppImage \
        https://github.com/86Box/86Box/releases/download/v6.0/86Box-Linux-x86_64-b9001.AppImage && \
    chmod +x /tmp/86box.AppImage && \
    cd /tmp && ./86box.AppImage --appimage-extract > /dev/null && \
    mv /tmp/squashfs-root /opt/86box && \
    rm -f /tmp/86box.AppImage && \
    git clone --depth 1 https://github.com/86Box/roms.git /opt/86box/roms && \
    rm -rf /opt/86box/roms/.git && \
    # fix appimage broken path
    patchelf --set-interpreter /lib64/ld-linux-x86-64.so.2 \
             --set-rpath '/opt/86box/lib/x86_64-linux-gnu:/opt/86box/usr/lib:/opt/86box/usr/lib/x86_64-linux-gnu' \
             /opt/86box/usr/local/bin/86Box && \
    chmod -R a+rX /opt/86box
COPY 86box.sh /usr/local/bin/86box
RUN chmod 755 /usr/local/bin/86box

# create venv
WORKDIR /app
COPY requirements.txt /app/
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r /app/requirements.txt && \
    chgrp -R users /opt/venv && \
    chmod -R g+rwX /opt/venv && \
    find /opt/venv -type d -exec chmod g+s {} \;
ENV VENV_PATH=/opt/venv


# build the pipewire module for xrdp audio
WORKDIR /tmp
RUN mkdir -p /app/pipewire-module && \
    git clone https://github.com/neutrinolabs/pipewire-module-xrdp.git /tmp/pipewire-module && \
    cd /tmp/pipewire-module && \
    ./bootstrap && \
    ./configure --with-module-dir=/usr/lib/x86_64-linux-gnu/pipewire-0.3 && \
    make -j4 && \
    make install && \
    ldconfig

COPY startaudio.sh /app/
RUN chmod +x /app/startaudio.sh
COPY entrypoint.sh /app
RUN chmod +x /app/entrypoint.sh


EXPOSE 3389 8080 22
ENTRYPOINT ["/app/entrypoint.sh"]