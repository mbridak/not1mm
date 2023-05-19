FROM python:latest

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install \
	libgl1 \
	libportaudio2 \
	libxcb-icccm4 \
	libxcb-image0 \
	libxcb-keysyms1 \
	libxcb-render-util0 \
	libxcb-shape0 \
	libxcb-xinerama0 \
	libxcb-xkb-dev \
	libxkbcommon-x11-0 \
	libdbus-1-3 \
	xdg-utils

RUN useradd -ms /bin/bash docker
USER docker

RUN pip install not1mm
RUN mkdir -p ~/.config/not1mm ~/.local/share/not1mm /tmp/xdg

ENV QT_DEBUG_PLUGINS=0
ENV QT_X11_NO_MITSHM=1
ENV _X11_NO_MITSHM=1
ENV _MITSHM=0
ENV XDG_RUNTIME_DIR=/tmp/xdg

ENTRYPOINT ["/home/docker/.local/bin/not1mm"]
CMD ["--help"]
