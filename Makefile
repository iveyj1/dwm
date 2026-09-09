# dwm - dynamic window manager
# See LICENSE file for copyright and license details.

include config.mk

SRC = drw.c dwm.c util.c
OBJ = ${SRC:.c=.o}

all: dwm dwm-spawn

.c.o:
	${CC} -c ${CFLAGS} $<

${OBJ}: config.h config.mk

config.h:
	cp config.def.h $@

dwm: ${OBJ}
	${CC} -o $@ ${OBJ} ${LDFLAGS}

dwm-spawn: dwm-spawn.c config.mk
	${CC} -o $@ ${CFLAGS} dwm-spawn.c -L${X11LIB} -lX11

clean:
	rm -f dwm dwm-spawn ${OBJ} dwm-${VERSION}.tar.gz

dist: clean
	mkdir -p dwm-${VERSION}
	cp -R LICENSE Makefile README config.def.h config.mk\
		dwm.1 drw.h util.h ${SRC} dwm-spawn.c dwm.png transient.c dwm-${VERSION}
	tar -cf dwm-${VERSION}.tar dwm-${VERSION}
	gzip dwm-${VERSION}.tar
	rm -rf dwm-${VERSION}

install: all
	mkdir -p ${DESTDIR}${PREFIX}/bin

	cp -f dwm \
		dwm-spawn\
		dwm-keymap\
		dwm-st-help\
		dwm-suspend\
		brightness-up\
		brightness-down\
		dwm-screenshot\
		dwm-screenshot-full\
		${DESTDIR}${PREFIX}/bin

	chmod 755 ${DESTDIR}${PREFIX}/bin/dwm \
		      ${DESTDIR}${PREFIX}/bin/dwm-spawn \
			  ${DESTDIR}${PREFIX}/bin/dwm-keymap \
			  ${DESTDIR}${PREFIX}/bin/dwm-st-help \
			  ${DESTDIR}${PREFIX}/bin/dwm-suspend \
			  ${DESTDIR}${PREFIX}/bin/brightness-up \
			  ${DESTDIR}${PREFIX}/bin/brightness-down \
			  ${DESTDIR}${PREFIX}/bin/dwm-screenshot \
			  ${DESTDIR}${PREFIX}/bin/dwm-screenshot-full 

	mkdir -p ${DESTDIR}${MANPREFIX}/man1
	sed "s/VERSION/${VERSION}/g" < dwm.1 > ${DESTDIR}${MANPREFIX}/man1/dwm.1
	chmod 644 ${DESTDIR}${MANPREFIX}/man1/dwm.1

uninstall:
	rm -f ${DESTDIR}${PREFIX}/bin/dwm ${DESTDIR}${PREFIX}/bin/dwm-spawn ${DESTDIR}${PREFIX}/bin/dwm-keymap\
		${DESTDIR}${PREFIX}/bin/dwm-st-help\
		${DESTDIR}${PREFIX}/bin/dwm-suspend\
		${DESTDIR}${PREFIX}/bin/brightness-up ${DESTDIR}${PREFIX}/bin/brightness-down\
		${DESTDIR}${MANPREFIX}/man1/dwm.1

.PHONY: all clean dist install uninstall
